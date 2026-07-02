from dotenv import load_dotenv
import os
import uuid
import importlib
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone
import streamlit as st

load_dotenv()
from config import load_config
from src.agents.orchestrator.factory import create_orchestrator
from src.guardrails import validate_minor_advisory
from src.memory import profile_store


DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
UI_STATE_PATH = DATA_DIR / "ui_threads.json"
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def _save_uploaded_pdf(uploaded_file) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{_safe_filename(uploaded_file.name)}"
    target_path = UPLOADS_DIR / filename
    target_path.write_bytes(uploaded_file.getbuffer())
    return target_path


def _resolve_agent_graph_module():
    module = importlib.import_module("src.agents.graph")
    has_chat = hasattr(module, "chat_with_openai") or hasattr(module, "chat_with_adk")
    has_extract = hasattr(module, "extract_profile_from_messages")

    # Streamlit hot-reload can leave a partially initialized module in sys.modules.
    if not (has_chat and has_extract):
        sys.modules.pop("src.agents.graph", None)
        module = importlib.import_module("src.agents.graph")
        has_chat = hasattr(module, "chat_with_openai") or hasattr(module, "chat_with_adk")
        has_extract = hasattr(module, "extract_profile_from_messages")

    if not (has_chat and has_extract):
        available = [name for name in dir(module) if "chat" in name.lower() or "extract" in name.lower()]
        raise AttributeError(
            "src.agents.graph is loaded but missing expected functions: "
            "chat_with_openai (or legacy alias chat_with_adk) and extract_profile_from_messages. "
            f"Available related symbols: {available}"
        )
    return module


st.set_page_config(page_title="Financial Advisor", page_icon=":money_with_wings:", layout="wide")
st.title("Financial Advisor :money_with_wings:")

st.markdown(
    """
    <style>
    :root {
        --bg: #f3f6fb;
        --surface: #ffffff;
        --surface-soft: #eef3fb;
        --text: #152238;
        --muted: #60708a;
        --accent: #1f6feb;
        --border: #dbe4f0;
        --shadow-lg: 0 14px 30px rgba(15, 23, 42, 0.12);
        --shadow-md: 0 10px 24px rgba(15, 23, 42, 0.08);
    }

    .stApp {
        background: radial-gradient(circle at 0% 0%, #e7eef9 0%, var(--bg) 45%, #f8faff 100%);
        color: var(--text);
    }

    .main .block-container {
        padding-top: 1.5rem;
        max-width: 980px;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f5f8fe 100%);
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] [data-testid="stButton"] > button {
        width: 100%;
        border-radius: 12px;
        border: 1px solid #d3deef;
        background: #ffffff;
        color: var(--text);
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
        font-weight: 600;
        transition: all 0.2s ease;
    }

    [data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
        transform: translateY(-1px);
        border-color: #b8c9e6;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
    }

    [data-testid="stChatInput"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        box-shadow: var(--shadow-md);
        padding: 0.15rem 0.35rem;
    }

    [data-testid="stChatMessage"] {
        border-radius: 16px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-md);
        margin-bottom: 0.7rem;
        overflow: hidden;
    }

    [data-testid="stChatMessage"][data-testid*="user"] {
        background: linear-gradient(180deg, #e8f1ff 0%, #dfeeff 100%);
    }

    [data-testid="stChatMessage"]:has([aria-label="assistant avatar"]) {
        background: linear-gradient(180deg, var(--surface) 0%, #fbfdff 100%);
    }

    .stMarkdown p {
        color: var(--text);
    }

    h1 {
        font-weight: 750;
        letter-spacing: -0.02em;
        color: #0f1f38;
        text-shadow: 0 2px 10px rgba(15, 31, 56, 0.08);
        margin-bottom: 0.4rem;
    }

    [data-testid="stStatusWidget"] {
        border-radius: 12px;
        box-shadow: var(--shadow-md);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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


def _load_persisted_ui_state() -> tuple[dict, dict]:
    if not UI_STATE_PATH.exists():
        return {}, {}
    try:
        payload = json.loads(UI_STATE_PATH.read_text(encoding="utf-8"))
        history = payload.get("chat_history_by_thread", {})
        meta = payload.get("thread_meta", {})
        if not isinstance(history, dict) or not isinstance(meta, dict):
            return {}, {}
        return history, meta
    except Exception:
        return {}, {}


def _persist_ui_state() -> None:
    payload = {
        "chat_history_by_thread": st.session_state.get("chat_history_by_thread", {}),
        "thread_meta": st.session_state.get("thread_meta", {}),
    }
    UI_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")


def _ensure_thread_initialized(thread_id: str) -> None:
    if "chat_history_by_thread" not in st.session_state:
        history, meta = _load_persisted_ui_state()
        st.session_state.chat_history_by_thread = history
        st.session_state.thread_meta = meta
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
            "last_statement_file_path": None,
            "last_statement_file_name": None,
            "last_statement_type": None,
        }
    _persist_ui_state()


def _thread_has_messages(thread_id: str) -> bool:
    history = st.session_state.chat_history_by_thread.get(thread_id, [])
    return len(history) > 0

if not os.getenv("OPENAI_API_KEY"):
    st.error("Please set the OPENAI_API_KEY environment variable.")
    st.stop()

# thread id - which conversation we are in - can be used for session management, or to link to a specific graph session
query_params = st.query_params

if "thread_id" in query_params:
    st.session_state.thread_id = query_params["thread_id"][0]
if "thread_id" not in st.session_state:
    persisted_history, persisted_meta = _load_persisted_ui_state()
    latest_non_empty = None
    if persisted_meta:
        ordered = sorted(
            persisted_meta.items(),
            key=lambda item: item[1].get("updated_at", ""),
            reverse=True,
        )
        for tid, _ in ordered:
            if len(persisted_history.get(tid, [])) > 0:
                latest_non_empty = tid
                break
    st.session_state.thread_id = latest_non_empty or str(uuid.uuid4())
    st.query_params["thread_id"] = st.session_state.thread_id

if "user_id" not in st.session_state:
    st.session_state.user_id = "default"

_ensure_thread_initialized(st.session_state.thread_id)

st.sidebar.subheader("Conversations")

profile = profile_store.load_profile(st.session_state.user_id)
get_profile_meta = getattr(profile_store, "get_last_profile_load_meta", None)
profile_load_meta = get_profile_meta() if callable(get_profile_meta) else {"mode": "unknown"}
profile_mode = profile_load_meta.get("mode", "none")

if profile_mode == "fallback":
    st.sidebar.info("Profile loaded in legacy-compatibility mode.")
elif profile_mode == "fallback-invalid":
    st.sidebar.warning("Stored profile format was invalid. Continuing with empty profile.")
elif profile_mode == "error":
    err_type = profile_load_meta.get("error_type", "UnknownError")
    err_msg = profile_load_meta.get("error_message", "")
    st.sidebar.error("Profile load failed. Continuing with empty profile.")
    with st.sidebar.expander("Profile load diagnostics"):
        st.text(f"mode={profile_mode}")
        st.text(f"error_type={err_type}")
        if err_msg:
            st.text(err_msg)

minor_advisory = validate_minor_advisory(profile) if profile is not None else None

if minor_advisory is not None and minor_advisory.guardian_required:
    st.sidebar.warning(
        "Minor profile detected. Guardian review is required before investment actions."
    )

if st.sidebar.button("+ New conversation", use_container_width=True):
    current_tid = st.session_state.thread_id
    # ChatGPT-like behavior: if current thread is still empty, reuse it.
    if _thread_has_messages(current_tid):
        new_thread_id = str(uuid.uuid4())
        st.session_state.thread_id = new_thread_id
        st.query_params["thread_id"] = new_thread_id
        _ensure_thread_initialized(new_thread_id)
        _persist_ui_state()
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
        _persist_ui_state()
        st.rerun()


history = st.session_state.chat_history_by_thread[st.session_state.thread_id]

st.markdown("Attach a PDF with your message (portfolio or bank statement):")
statement_pdf = st.file_uploader(
    "Attach PDF",
    type=["pdf"],
    key=f"chat_attachment_{st.session_state.thread_id}",
    label_visibility="collapsed",
)
pdf_password = st.text_input(
    "PDF password (only if required)",
    type="password",
    value="",
    help="Used only to open encrypted statements for this request.",
)

thread_meta = st.session_state.thread_meta.get(st.session_state.thread_id, {})
remembered_statement_name = thread_meta.get("last_statement_file_name")
if remembered_statement_name:
    st.caption(f"Remembered statement for this conversation: {remembered_statement_name}")

if minor_advisory is not None and minor_advisory.guardian_required:
    st.warning(
        "Minor Safety Mode is active. Recommendations are educational-first and conservatively risk-capped."
    )

for msg in history:
    if msg.get("role") == "user":
        st.chat_message("user").write(msg.get("content", ""))
    elif msg.get("role") == "assistant":
        with st.chat_message("assistant"):
            st.write(msg.get("content", ""))
            spend_chart = msg.get("spend_chart")
            if isinstance(spend_chart, list) and spend_chart:
                try:
                    import pandas as pd

                    df = pd.DataFrame(spend_chart)
                    if not df.empty and {"category", "amount_inr"}.issubset(df.columns):
                        st.bar_chart(df.set_index("category")["amount_inr"])
                except Exception:
                    pass

            spend_suggestions = msg.get("spend_suggestions")
            if isinstance(spend_suggestions, list) and spend_suggestions:
                st.caption("Suggestions")
                for item in spend_suggestions[:5]:
                    st.write(f"- {item}")

if prompt:=st.chat_input("Ask me anything about personal finance! (attach PDF above if needed)"):
    orchestrator.logger.info("Received user prompt", extra={"user_id": st.session_state.user_id})
    history.append({"role": "user", "content": prompt})
    st.session_state.thread_meta[st.session_state.thread_id]["updated_at"] = _utc_now_iso()
    if st.session_state.thread_meta[st.session_state.thread_id].get("title", "").startswith("Started "):
        st.session_state.thread_meta[st.session_state.thread_id]["title"] = _truncate_title(prompt)
    _persist_ui_state()
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        thinking = st.empty()
        thinking.write("Thinking...")

        agent_graph = _resolve_agent_graph_module()
        chat_fn = getattr(agent_graph, "chat_with_openai", None) or getattr(agent_graph, "chat_with_adk", None)
        if chat_fn is None:
            raise AttributeError("Missing chat helper in src.agents.graph")

        response_text = ""
        assistant_msg: dict[str, object] = {"role": "assistant", "content": ""}
        prompt_lower = prompt.lower()
        statement_tokens = [
            "statement",
            "spend",
            "spent",
            "spending",
            "expense",
            "budget",
            "merchant",
            "transaction",
            "pdf",
        ]

        saved_path: str | None = None
        if statement_pdf is not None:
            uploaded_path = _save_uploaded_pdf(statement_pdf)
            saved_path = str(uploaded_path)
            st.session_state.thread_meta[st.session_state.thread_id]["last_statement_file_path"] = saved_path
            st.session_state.thread_meta[st.session_state.thread_id]["last_statement_file_name"] = statement_pdf.name
            st.session_state.thread_meta[st.session_state.thread_id]["last_statement_type"] = "uploaded_pdf"
            user_attachment_note = f"\n[Attached statement: {statement_pdf.name}]"
            history[-1]["content"] = f"{history[-1]['content']}{user_attachment_note}"
        else:
            remembered_path = st.session_state.thread_meta[st.session_state.thread_id].get("last_statement_file_path")
            if remembered_path and any(token in prompt_lower for token in statement_tokens):
                if Path(remembered_path).exists():
                    saved_path = remembered_path

        if saved_path is not None:
            password_value = pdf_password.strip() or None
            spend_mode = any(
                token in prompt_lower
                for token in [
                    "spend",
                    "spent",
                    "spending",
                    "expense",
                    "categor",
                    "classif",
                    "budget",
                    "blinkit",
                    "instamart",
                    "zepto",
                    "how much",
                ]
            )

            if spend_mode:
                classify_fn = getattr(agent_graph, "classify_spends_from_pdf", None)
                if callable(classify_fn):
                    result = classify_fn(
                        user_id=st.session_state.user_id,
                        thread_id=st.session_state.thread_id,
                        file_path=str(saved_path),
                        document_type="bank_statement",
                        password=password_value,
                        user_query=prompt,
                    )
                    response_text = str(result.get("analysis_text", "I could not classify spends from this file."))
                    spend_payload = result.get("spend_analysis")
                    if isinstance(spend_payload, dict):
                        categories = spend_payload.get("categories", [])
                        if isinstance(categories, list):
                            assistant_msg["spend_chart"] = categories
                        suggestions = spend_payload.get("budget_suggestions", [])
                        if isinstance(suggestions, list):
                            assistant_msg["spend_suggestions"] = suggestions
                else:
                    response_text = "Spend analysis agent is not available right now."
            else:
                advise_fn = getattr(agent_graph, "advise_from_pdf", None)
                if callable(advise_fn):
                    result = advise_fn(
                        user_id=st.session_state.user_id,
                        thread_id=st.session_state.thread_id,
                        file_path=str(saved_path),
                        document_type="auto",
                        password=password_value,
                    )
                    response_text = str(result.get("analysis_text", "I could not analyze this statement."))
                else:
                    response_text = "PDF analysis agent is not available right now."
        else:
            response_text = chat_fn(
                user_id=st.session_state.user_id,
                thread_id=st.session_state.thread_id,
                message=prompt,
            )

        assistant_msg["content"] = response_text
        history.append(assistant_msg)
        st.session_state.thread_meta[st.session_state.thread_id]["updated_at"] = _utc_now_iso()
        _persist_ui_state()
        orchestrator.memory.set(f"summary:{st.session_state.user_id}", response_text)
        agent_graph.extract_profile_from_messages(
            messages=history,
            user_id=st.session_state.user_id,
            thread_id=st.session_state.thread_id,
        )

        thinking.empty()
        st.write(response_text)
    #st.rerun()