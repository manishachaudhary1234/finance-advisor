import os
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google import genai

# Compatibility shim: some environments expose ADK expecting this symbol even when
# the installed google.genai package does not define it.
if not hasattr(genai.types, "TranslationConfig"):
    class TranslationConfig:  # pragma: no cover - defensive compatibility class
        pass

    genai.types.TranslationConfig = TranslationConfig

try:
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    _ADK_AVAILABLE = True
    _ADK_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - depends on local environment packages
    Agent = None
    Runner = None
    InMemorySessionService = None
    _ADK_AVAILABLE = False
    _ADK_IMPORT_ERROR = exc
from google.genai import types as genai_types

from src.memory.events_store import add_event
from src.memory.profile_store import load_profile, merge_profile_update
from src.schemas.events import MemoryEvent
from src.schemas.updates import ProfileUpdate

load_dotenv()

IST = ZoneInfo("Asia/Calcutta")


def _cfg(config: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not config:
        return {}
    configurable = config.get("configurable")
    return configurable if isinstance(configurable, dict) else {}


def _user_id(config: Optional[dict[str, Any]]) -> str:
    return _cfg(config).get("user_id", "default")


def _thread_id(config: Optional[dict[str, Any]]) -> Optional[str]:
    value = _cfg(config).get("thread_id")
    return str(value) if value is not None else None


def _message_content(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("content", ""))
    content = getattr(message, "content", None)
    if content is None:
        return str(message)
    return str(content)


def _role_name(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("role", "user")).lower()
    role = getattr(message, "role", None)
    if role:
        return str(role).lower()
    name = type(message).__name__.lower()
    if "human" in name or "user" in name:
        return "user"
    return "assistant"


def _update_is_empty(update: ProfileUpdate) -> bool:
    data = update.model_dump(exclude={"new_exclusions", "should_log_event", "event_summary"})
    if any(v is not None for v in data.values()):
        return False
    return not update.new_exclusions


def _to_gemini_schema(schema: dict, defs: Optional[dict] = None) -> dict:
    if defs is None:
        defs = schema.get("$defs", {})
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        return _to_gemini_schema(defs[ref_name], defs)
    if "anyOf" in schema:
        non_null = [s for s in schema["anyOf"] if s.get("type") != "null"]
        result = _to_gemini_schema(non_null[0], defs) if non_null else {"type": "string"}
        result["nullable"] = True
        return result

    result: dict[str, Any] = {}
    if "type" in schema:
        result["type"] = schema["type"]
    if "enum" in schema:
        result["enum"] = schema["enum"]
    if "properties" in schema:
        result["type"] = "object"
        result["properties"] = {k: _to_gemini_schema(v, defs) for k, v in schema["properties"].items()}
    if "items" in schema:
        result["items"] = _to_gemini_schema(schema["items"], defs)
    if "required" in schema:
        result["required"] = schema["required"]
    return result


def _extract_text_from_event(event: Any) -> str:
    content = getattr(event, "content", None)
    if not content:
        return ""
    parts = getattr(content, "parts", None) or []
    text_parts: list[str] = []
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            text_parts.append(text)
    return "".join(text_parts).strip()


class ADKFinanceAdvisor:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.app_name = "finance-advisor"
        self.session_service = InMemorySessionService() if _ADK_AVAILABLE else None

    def _build_instruction(self, user_id: str) -> str:
        profile = load_profile(user_id)
        profile_json = profile.model_dump_json(exclude_none=True) if profile else "{}"
        return (
            "You are a financial advisor for Indian investors.\n"
            f"Known User Profile (long_term_memory):\n{profile_json}\n\n"
            "Use this profile to personalise advice. "
            "If important fields are missing (income, goals, risk), ask clarifying questions "
            "before recommending specific products. "
            "Do not invent profile facts that are not shown above."
        )

    def chat(self, *, user_id: str, thread_id: str, message: str) -> str:
        if not _ADK_AVAILABLE:
            profile = load_profile(user_id)
            profile_json = profile.model_dump_json(exclude_none=True) if profile else "{}"
            fallback_prompt = (
                "You are a financial advisor for Indian investors.\n"
                f"Known User Profile (long_term_memory):\n{profile_json}\n\n"
                "Use this profile to personalise advice. "
                "If important fields are missing (income, goals, risk), ask clarifying questions."
            )
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=message,
                config=genai.types.GenerateContentConfig(
                    system_instruction=fallback_prompt,
                    temperature=0.2,
                ),
            )
            return response.text or "I could not generate a response right now."

        agent = Agent(
            name="finance_advisor",
            model="gemini-2.5-flash",
            instruction=self._build_instruction(user_id),
        )
        runner = Runner(
            app_name=self.app_name,
            agent=agent,
            session_service=self.session_service,
            auto_create_session=True,
        )

        events = runner.run(
            user_id=user_id,
            session_id=thread_id,
            new_message=genai_types.UserContent(
                parts=[genai_types.Part.from_text(text=message)]
            ),
        )

        final_text = ""
        for event in events:
            text = _extract_text_from_event(event)
            if text:
                final_text = text

        return final_text or "I could not generate a response right now."


EXTRACT_PROMPT = """Extract financial profile updates from this conversation for an Indian investor.
Rules:
- Only extract facts the user clearly stated. Do not guess.
- Leave fields null if not mentioned.
- Amounts are in INR.
- risk_tolerance must be: low, medium, or high.
- primary_goal examples: retirement, education, wealth_accumulation, emergency_fund, other
- Put exclusions (crypto, sector funds, etc.) in new_exclusions.
- Set should_log_event=true if user corrected a fact, rejected something,
  or said \"remember this\". Put a one-sentence summary in event_summary.
Existing profile:
{profile_json}
Recent conversation:
{conversation}
"""


_advisor = ADKFinanceAdvisor()


def chat_with_adk(user_id: str, thread_id: str, message: str) -> str:
    return _advisor.chat(user_id=user_id, thread_id=thread_id, message=message)


def extract_profile_from_messages(messages: list[dict[str, str]], user_id: str, thread_id: Optional[str]) -> None:
    profile = load_profile(user_id)
    profile_json = profile.model_dump_json(exclude_none=True) if profile else "{}"

    recent = messages[-6:]
    conversation = "\n".join(
        f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}" for m in recent
    )

    extraction_prompt = EXTRACT_PROMPT.format(
        profile_json=profile_json,
        conversation=conversation,
    )

    gemini_schema = _to_gemini_schema(ProfileUpdate.model_json_schema())

    try:
        response = _advisor.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=extraction_prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=gemini_schema,
            ),
        )
        update = ProfileUpdate.model_validate_json(response.text)
    except Exception:
        update = ProfileUpdate()

    if not _update_is_empty(update):
        merge_profile_update(user_id, update)

    if update.should_log_event and update.event_summary:
        add_event(
            MemoryEvent(
                user_id=user_id,
                event_type="note",
                content=update.event_summary,
                created_at=datetime.now(IST),
                source_thread_id=thread_id,
            )
        )


# Backward-compatible wrappers for old test scripts.
def chatbot(state: dict[str, Any], config: Optional[dict[str, Any]] = None) -> dict[str, list[dict[str, str]]]:
    user_id = _user_id(config)
    thread_id = _thread_id(config) or "default-thread"
    messages = state.get("messages", [])
    user_message = _message_content(messages[-1]) if messages else ""
    reply = chat_with_adk(user_id=user_id, thread_id=thread_id, message=user_message)
    return {"messages": [{"role": "assistant", "content": reply}]}


def extract_profile(state: dict[str, Any], config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    user_id = _user_id(config)
    thread_id = _thread_id(config)
    normalized = [
        {"role": _role_name(message), "content": _message_content(message)}
        for message in state.get("messages", [])
    ]
    extract_profile_from_messages(normalized, user_id=user_id, thread_id=thread_id)
    return {}
