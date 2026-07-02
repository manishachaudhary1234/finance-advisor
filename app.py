from dotenv import load_dotenv
import os
import uuid
import importlib
import sys
from datetime import datetime, timezone
import streamlit as st

load_dotenv()
from config import load_config
from src.agents.orchestrator.factory import create_orchestrator
from src.memory.profile_store import load_profile


def _resolve_agent_graph_module():
    module = importlib.import_module("src.agent.graph")
    has_chat = hasattr(module, "chat_with_adk")
    has_extract = hasattr(module, "extract_profile_from_messages")

    # Streamlit hot-reload can leave a partially initialized module in sys.modules.
    if not (has_chat and has_extract):
        sys.modules.pop("src.agent.graph", None)
        module = importlib.import_module("src.agent.graph")
        has_chat = hasattr(module, "chat_with_adk")
        has_extract = hasattr(module, "extract_profile_from_messages")

    if not (has_chat and has_extract):
        available = [name for name in dir(module) if "chat" in name.lower() or "extract" in name.lower()]
        raise AttributeError(
            "src.agent.graph is loaded but missing expected functions: "
            "chat_with_adk/extract_profile_from_messages. "
            f"Available related symbols: {available}"
        )
    return module


st.set_page_config(page_title="Financial Advisor", page_icon=":money_with_wings:", layout="wide")
st.title("Financial Advisor :money_with_wings:")

try:
    app_config = load_config("config.yml")
except Exception as exc:
    st.error(f"Failed to load configuration: {exc}")
    st.stop()

os.environ["PROFILES_DB_PATH"] = app_config.memory.profiles_db_path
os.environ["EVENTS_DB_PATH"] = app_config.memory.events_db_path

orchestrator = create_orchestrator(
    memory_store_kind=app_config.memory.backend,
    prompt_repo_kind=app_config.prompts.backend,
    prompt_base_dir=app_config.prompts.base_dir,
    logger_name=app_config.logging.name,
    logger_level=app_config.logging.level,
    logger_file_path=app_config.logging.file_path,
)
orchestrator.logger.info("App booted with config.yml via config.py")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _starter_title() -> str:
    # Provide a stable placeholder so untitled chats are still identifiable.
    return datetime.now().strftime("Started %d %b, %H:%M")


def _truncate_title(text: str, max_len: int = 34) -> str:
    cleaned = " ".join(text.strip().split())
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[:max_len - 3]}..."


def _ensure_thread_initialized(thread_id: str) -> None:
    if "chat_history_by_thread" not in st.session_state:
        st.session_state.chat_history_by_thread = {}
    if "thread_meta" not in st.session_state:
        st.session_state.thread_meta = {}

    if thread_id not in st.session_state.chat_history_by_thread:
        st.session_state.chat_history_by_thread[thread_id] = []

    if thread_id not in st.session_state.thread_meta:
        now = _utc_now_iso()
        st.session_state.thread_meta[thread_id] = {
            "title": _starter_title(),
            "created_at": now,
            "updated_at": now,
        }


def _thread_has_messages(thread_id: str) -> bool:
    history = st.session_state.chat_history_by_thread.get(thread_id, [])
    return len(history) > 0

if not os.getenv("GOOGLE_API_KEY"):
    st.error("Please set the GOOGLE_API_KEY environment variable.")
    st.stop()

# thread id - which conversation we are in - can be used for session management, or to link to a specific graph session
query_params = st.query_params

if "thread_id" in query_params:
    st.session_state.thread_id = query_params["thread_id"][0]
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    st.query_params["thread_id"] = st.session_state.thread_id

if "user_id" not in st.session_state:
    st.session_state.user_id = "default"

_ensure_thread_initialized(st.session_state.thread_id)

st.sidebar.subheader("Conversations")

if st.sidebar.button("+ New conversation", use_container_width=True):
    current_tid = st.session_state.thread_id
    # ChatGPT-like behavior: if current thread is still empty, reuse it.
    if _thread_has_messages(current_tid):
        new_thread_id = str(uuid.uuid4())
        st.session_state.thread_id = new_thread_id
        st.query_params["thread_id"] = new_thread_id
        _ensure_thread_initialized(new_thread_id)
    st.rerun()

thread_items = sorted(
    st.session_state.thread_meta.items(),
    key=lambda item: item[1].get("updated_at", ""),
    reverse=True,
)

for tid, meta in thread_items:
    # Hide empty inactive threads to avoid duplicate "new conversation" rows.
    if tid != st.session_state.thread_id and not _thread_has_messages(tid):
        continue
    title = meta.get("title") or "New conversation"
    active_prefix = "● " if tid == st.session_state.thread_id else ""
    label = f"{active_prefix}{_truncate_title(title)}"
    if st.sidebar.button(label, key=f"conv_{tid}", use_container_width=True):
        st.session_state.thread_id = tid
        st.query_params["thread_id"] = tid
        _ensure_thread_initialized(tid)
        st.rerun()


history = st.session_state.chat_history_by_thread[st.session_state.thread_id]

for msg in history:
    if msg.get("role") == "user":
        st.chat_message("user").write(msg.get("content", ""))
    elif msg.get("role") == "assistant":
        st.chat_message("assistant").write(msg.get("content", ""))

if prompt:=st.chat_input("Ask me anything about personal finance!"):
    orchestrator.logger.info("Received user prompt", extra={"user_id": st.session_state.user_id})
    history.append({"role": "user", "content": prompt})
    st.session_state.thread_meta[st.session_state.thread_id]["updated_at"] = _utc_now_iso()
    if st.session_state.thread_meta[st.session_state.thread_id].get("title", "").startswith("Started "):
        st.session_state.thread_meta[st.session_state.thread_id]["title"] = _truncate_title(prompt)
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        thinking = st.empty()
        thinking.write("Thinking...")

        agent_graph = _resolve_agent_graph_module()

        response_text = agent_graph.chat_with_adk(
            user_id=st.session_state.user_id,
            thread_id=st.session_state.thread_id,
            message=prompt,
        )

        history.append({"role": "assistant", "content": response_text})
        st.session_state.thread_meta[st.session_state.thread_id]["updated_at"] = _utc_now_iso()
        orchestrator.memory.set(f"summary:{st.session_state.user_id}", response_text)
        agent_graph.extract_profile_from_messages(
            messages=history,
            user_id=st.session_state.user_id,
            thread_id=st.session_state.thread_id,
        )

        thinking.empty()
        st.write(response_text)
    #st.rerun()