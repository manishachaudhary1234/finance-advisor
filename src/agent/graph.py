import sqlite3
from pathlib import Path
import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.runnables import RunnableConfig
from zoneinfo import ZoneInfo
from typing import Optional

from src.agent.state import AgentState
from src.schemas.updates import ProfileUpdate
from src.memory.profile_store import load_profile, merge_profile_update
from src.memory.events_store import add_event
from src.schemas.events import MemoryEvent
from datetime import datetime

IST = ZoneInfo("Asia/Calcutta")

# 1. LLM

llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.2)
extractor = llm.with_structured_output(ProfileUpdate)

def _cfg(config: RunnableConfig) -> dict:
    return config.get("configurable",{}) or {}

def _user_id(config: RunnableConfig) -> str:
    return _cfg(config).get("user_id","default")

def _thread_id(config: RunnableConfig) -> Optional[str]:
    return _cfg(config).get("thread_id")

def _update_is_empty(update: ProfileUpdate)->bool:
    data = update.model_dump(exclude={"new_exclusions","should_log_event","event_summary"})
    print("dat------", data)
    if any(v is not None for v in data.values()):
        return False
    return not update.new_exclusions

# 2. The one Node

def chatbot(state: AgentState, config: RunnableConfig):
    user_id = _user_id(config)
    profile = load_profile(user_id)

    profile_json = (profile.model_dump_json(exclude_none=True)
                    if profile else "{}")
    
    system = SystemMessage(content=f"""
                                You are a financial advisor for Indian investors.
                                Known User Profile(long_term_memory)
                                    {profile_json}
                                Use this profile to personalise advise.
                                If important fields are missing (income, goals, risk), ask clarifying questions 
                                before recommending specific products.
                                Do not invent profile facts that are not shown above
                            """)
    response = llm.invoke([system, *state["messages"]])  
    return {"messages": [response]}


EXTRACT_PROMPT = """Extract financial profile updates from this conversation for an Indian investor.
Rules:
- Only extract facts the user clearly stated. Do not guess.
- Leave fields null if not mentioned.
- Amounts are in INR.
- risk_tolerance must be: low, medium, or high.
- primary_goal examples: retirement, education, wealth_accumulation, emergency_fund, other
- Put exclusions (crypto, sector funds, etc.) in new_exclusions.
- Set should_log_event=true if user corrected a fact, rejected something,
  or said "remember this". Put a one-sentence summary in event_summary.
Existing profile:
{profile_json}
Recent conversation:
{conversation}
"""

def extract_profile(state: AgentState, config: RunnableConfig):
    user_id = _user_id(config)
    thread_id = _thread_id(config)

    profile = load_profile(user_id)
    profile_json = profile.model_dump_json(exclude_none=True) if profile else "{}"

    recent = state["messages"][-6:]
    conversation = "\n".join(
        f"{type(m).__name__}: {m.content}"
        for m in recent
        if getattr(m,"content", None)
    )

    update = extractor.invoke(
        EXTRACT_PROMPT.format(
            profile_json = profile_json,
            conversation = conversation
        )
    )

    if not _update_is_empty(update):
        merge_profile_update(user_id, update)

    if update.should_log_event and update.event_summary:
        add_event(
            MemoryEvent(
                user_id = user_id,
                event_type = "note",
                content = update.event_summary,
                created_at = datetime.now(IST),
                source_thread_id = thread_id
            )
        )

    return {}


#3. Wire the graph
builder = StateGraph(AgentState)
builder.add_node("chatbot", chatbot)
builder.add_node("extract", extract_profile)
builder.set_entry_point("chatbot")
builder.add_edge("chatbot","extract")
builder.add_edge("extract", END)

#4. checkpointing
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(exist_ok=True)
conn = sqlite3.connect(str(DATA_DIR / "sessions.db"), check_same_thread=False)
checkpointer = SqliteSaver(conn)

#compile
graph = builder.compile(checkpointer=checkpointer)

