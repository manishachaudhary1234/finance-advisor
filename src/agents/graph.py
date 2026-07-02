import os
import json
import re
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from openai import OpenAI

from src.memory.events_store import add_event, get_recent_events
from src.memory.profile_store import load_profile, merge_profile_update
from src.ingestion.parsers.pdf_parser import parse_pdf_statement
from src.guardrails import validate_minor_advisory
from src.schemas.events import MemoryEvent
from src.schemas.recommendation import RecommendationResponse
from src.schemas.spend_analysis import SpendAnalysisResponse
from src.schemas.updates import ProfileUpdate
from src.tools.schemas.tool_definitions import PdfIngestionInput

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


class OpenAIFinanceAdvisor:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def _build_instruction(self, user_id: str) -> str:
        profile = load_profile(user_id)
        profile_json = profile.model_dump_json(exclude_none=True) if profile else "{}"
        recent_events = get_recent_events(user_id=user_id, limit=8)
        events_text = "\n".join(
            f"- [{event.event_type}] {event.content}" for event in recent_events
        ) if recent_events else "- none"

        minor_guardrail_section = ""
        if profile is not None:
            minor_result = validate_minor_advisory(profile)
            if minor_result.guardian_required:
                warning_lines = "\n".join(f"- {warning}" for warning in minor_result.warnings)
                minor_guardrail_section = (
                    "\n\nMinor Safety Guardrails:\n"
                    "- This user is a minor. Keep advice educational and conservative.\n"
                    f"- Enforce risk cap: {minor_result.recommended_risk_cap}.\n"
                    "- Require guardian review before any action-oriented recommendation.\n"
                    f"{warning_lines}"
                )

        return (
            "You are a financial advisor for Indian investors.\n"
            f"Known User Profile (long_term_memory):\n{profile_json}\n\n"
            f"Recent Long-Term Memory Events:\n{events_text}\n\n"
            "Use this profile to personalise advice. "
            "Use recent memory events to align with user answer preferences and recurring spending/investment patterns. "
            "If important fields are missing (income, goals, risk), ask clarifying questions "
            "before recommending specific products. "
            "Do not invent profile facts that are not shown above."
            f"{minor_guardrail_section}"
        )


def _store_statement_analysis_event(
    *,
    user_id: str,
    thread_id: str,
    event_type: str,
    summary: str,
) -> None:
    try:
        add_event(
            MemoryEvent(
                user_id=user_id,
                event_type=event_type,
                content=summary,
                created_at=datetime.now(IST),
                source_thread_id=thread_id,
            )
        )
    except Exception:
        # Memory persistence should not break user-facing response flow.
        pass

    def chat(self, *, user_id: str, thread_id: str, message: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": self._build_instruction(user_id)},
                {"role": "user", "content": message},
            ],
        )

        final_text = completion.choices[0].message.content if completion.choices else None
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


_advisor = OpenAIFinanceAdvisor()


def _format_recommendation_text(rec: RecommendationResponse, *, source_label: str) -> str:
    lines: list[str] = [
        f"I analyzed your {source_label} and prepared a structured allocation idea.",
        "",
        f"Confidence: {rec.confidence_score:.2f}",
    ]

    if rec.assumptions:
        lines.append("Assumptions:")
        lines.extend(f"- {item}" for item in rec.assumptions[:4])

    if rec.recommendations:
        lines.append("")
        lines.append("Suggested instruments:")
        for item in rec.recommendations[:6]:
            lines.append(
                f"- {item.instrument_name} ({item.instrument_type}) - {item.allocation_pct:.1f}% [{item.risk_level}]"
            )
            lines.append(f"  Why: {item.rationale}")

    if rec.key_risks:
        lines.append("")
        lines.append("Key risks to monitor:")
        lines.extend(f"- {risk}" for risk in rec.key_risks[:4])

    if rec.rebalancing_triggers:
        lines.append("")
        lines.append("Rebalancing triggers:")
        lines.extend(f"- {trigger}" for trigger in rec.rebalancing_triggers[:4])

    if rec.next_review_date is not None:
        lines.append("")
        lines.append(f"Next review date: {rec.next_review_date.isoformat()}")

    return "\n".join(lines)


def _format_spend_analysis_text(report: SpendAnalysisResponse) -> str:
    lines: list[str] = [
        "I categorized your spending and prepared optimization suggestions.",
        "",
        f"Estimated total spend: INR {report.total_spend_inr:,.0f}",
        f"Confidence: {report.confidence_score:.2f}",
    ]

    if report.categories:
        lines.append("")
        lines.append("Top spend categories:")
        for item in report.categories[:6]:
            lines.append(f"- {item.category}: INR {item.amount_inr:,.0f} ({item.pct_of_total:.1f}%)")

    if report.savings_opportunities:
        lines.append("")
        lines.append("Savings opportunities:")
        lines.extend(f"- {item}" for item in report.savings_opportunities[:5])

    if report.budget_suggestions:
        lines.append("")
        lines.append("Suggested actions:")
        lines.extend(f"- {item}" for item in report.budget_suggestions[:5])

    return "\n".join(lines)


_MERCHANT_STOPWORDS = {
    "how",
    "much",
    "spent",
    "spend",
    "spending",
    "on",
    "at",
    "for",
    "from",
    "in",
    "my",
    "the",
    "and",
    "or",
    "to",
    "can",
    "you",
    "check",
    "show",
    "tell",
    "statement",
    "bank",
}


def _extract_amount_from_line(line: str) -> float | None:
    matches = re.findall(
        r"(?:inr|rs\.?|₹)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
        line,
        flags=re.IGNORECASE,
    )
    if not matches:
        return None
    # Transaction lines often include date/time before amount. The last numeric token
    # is usually closest to the debit/credit value in bank statements.
    candidate = matches[-1].replace(",", "")
    try:
        return float(candidate)
    except ValueError:
        return None


def _extract_merchants_from_query(user_query: str | None) -> list[str]:
    if not user_query:
        return []

    query = user_query.strip().lower()
    if not query:
        return []

    # Try to focus on the phrase after "on" for prompts like
    # "how much spent on x/y/z".
    search_area = query
    match = re.search(r"\bon\b\s+(.+)", query)
    if match:
        search_area = match.group(1)

    tokens = re.split(r"[/,;&]|\band\b|\bor\b", search_area)
    merchants: list[str] = []
    seen: set[str] = set()

    for token in tokens:
        cleaned = re.sub(r"[^a-z0-9 ._-]", " ", token).strip()
        if not cleaned:
            continue
        words = [w for w in cleaned.split() if w not in _MERCHANT_STOPWORDS]
        candidate = " ".join(words).strip()
        if len(candidate) < 2:
            continue
        if candidate not in seen:
            seen.add(candidate)
            merchants.append(candidate)

    return merchants


def _extract_merchant_spend_totals(text: str, merchants: list[str]) -> dict[str, float]:
    totals: dict[str, float] = {name: 0.0 for name in merchants}
    if not text:
        return totals

    merchant_tokens: dict[str, list[str]] = {}
    merchant_compact: dict[str, str] = {}
    for merchant in merchants:
        tokens = [token for token in re.split(r"\s+", merchant.lower()) if len(token) >= 2]
        merchant_tokens[merchant] = tokens
        merchant_compact[merchant] = re.sub(r"[^a-z0-9]", "", merchant.lower())

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        low = line.lower()
        compact_line = re.sub(r"[^a-z0-9]", "", low)

        amount = _extract_amount_from_line(line)
        if amount is None:
            continue

        for merchant in merchants:
            if merchant in low:
                totals[merchant] += amount
                continue

            # Fuzzy path for narration variants: "SWIGGY*INSTAMART", "AMAZONPAY" etc.
            compact_merchant = merchant_compact[merchant]
            if compact_merchant and compact_merchant in compact_line:
                totals[merchant] += amount
                continue

            tokens = merchant_tokens[merchant]
            if tokens and all(token in low for token in tokens):
                totals[merchant] += amount

    return totals


def advise_from_pdf(
    *,
    user_id: str,
    thread_id: str,
    file_path: str,
    document_type: str = "auto",
    password: str | None = None,
) -> dict[str, Any]:
    payload = PdfIngestionInput(
        user_id=user_id,
        session_id=thread_id,
        file_path=file_path,
        document_type=document_type,
        password=password,
    )
    ingestion = parse_pdf_statement(payload)

    if not ingestion.success:
        return {
            "success": False,
            "analysis_text": (
                "I could not read this PDF. Please upload a text-based bank or portfolio statement. "
                f"Details: {'; '.join(ingestion.warnings) if ingestion.warnings else ingestion.message}"
            ),
            "ingestion": ingestion.model_dump(mode="json"),
        }

    profile = load_profile(user_id)
    profile_json = profile.model_dump_json(exclude_none=True) if profile else "{}"
    schema_json = json.dumps(RecommendationResponse.model_json_schema(), ensure_ascii=True)

    prompt = (
        "You are a financial advisor for Indian investors. "
        "Use the extracted statement text and user profile to produce a diversified recommendation "
        "that can include mutual funds, ETFs, bonds, gold, and cash allocation as needed. "
        "Avoid concentrated bets. Keep risk suitable to profile.\n\n"
        f"Profile JSON:\n{profile_json}\n\n"
        f"Statement document_type_detected: {ingestion.document_type_detected}\n"
        f"Statement text preview:\n{ingestion.text_preview}\n"
    )

    try:
        completion = _advisor.client.chat.completions.create(
            model=_advisor.model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON only. Follow this JSON schema exactly:\n"
                        f"{schema_json}"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        response_text = completion.choices[0].message.content if completion.choices else "{}"
        parsed = json.loads(response_text or "{}")

        parsed.setdefault("user_id", user_id)
        parsed.setdefault("session_id", thread_id)
        parsed.setdefault("confidence_score", 0.5)
        parsed.setdefault("recommendations", [])
        parsed.setdefault("assumptions", [])
        parsed.setdefault("key_risks", [])
        parsed.setdefault("rebalancing_triggers", [])

        recommendation = RecommendationResponse.model_validate(parsed)
        top_items = recommendation.recommendations[:3]
        top_items_text = ", ".join(
            f"{item.instrument_name}:{item.allocation_pct:.0f}%" for item in top_items
        ) if top_items else "none"
        summary = (
            f"Statement analyzed ({ingestion.document_type_detected}); "
            f"confidence={recommendation.confidence_score:.2f}; top_recommendations={top_items_text}"
        )
        _store_statement_analysis_event(
            user_id=user_id,
            thread_id=thread_id,
            event_type="recommendation",
            summary=summary,
        )
        return {
            "success": True,
            "analysis_text": _format_recommendation_text(
                recommendation,
                source_label=ingestion.document_type_detected.replace("_", " "),
            ),
            "recommendation": recommendation.model_dump(mode="json"),
            "ingestion": ingestion.model_dump(mode="json"),
        }
    except Exception:
        fallback_text = (
            "I could read your PDF, but I need a bit more clarity before precise mutual fund/ETF suggestions. "
            "Please confirm your risk tolerance (low/medium/high), target horizon in years, and monthly investable amount."
        )
        return {
            "success": True,
            "analysis_text": fallback_text,
            "ingestion": ingestion.model_dump(mode="json"),
        }


def classify_spends_from_pdf(
    *,
    user_id: str,
    thread_id: str,
    file_path: str,
    document_type: str = "bank_statement",
    password: str | None = None,
    user_query: str | None = None,
) -> dict[str, Any]:
    payload = PdfIngestionInput(
        user_id=user_id,
        session_id=thread_id,
        file_path=file_path,
        document_type=document_type,
        password=password,
    )
    ingestion = parse_pdf_statement(payload)

    if not ingestion.success:
        return {
            "success": False,
            "analysis_text": (
                "I could not read this statement. Please upload a text-based bank statement PDF. "
                f"Details: {'; '.join(ingestion.warnings) if ingestion.warnings else ingestion.message}"
            ),
            "ingestion": ingestion.model_dump(mode="json"),
        }

    schema_json = json.dumps(SpendAnalysisResponse.model_json_schema(), ensure_ascii=True)
    merchants = _extract_merchants_from_query(user_query)
    merchant_totals = _extract_merchant_spend_totals(ingestion.text_preview, merchants)
    merchant_total_text = ", ".join(
        f"{name}=INR {value:,.0f}" for name, value in merchant_totals.items() if value > 0
    )
    if merchants and not merchant_total_text:
        merchant_total_text = "No clear entries found for requested merchants in extracted text."
    if not merchants:
        merchant_total_text = "No merchant names were detected in user query."

    prompt = (
        "Classify and summarize spending from the provided statement text. "
        "Estimate category totals in INR, percentage split, cost drivers, and practical savings actions.\n"
        "If the user asks for specific merchants, answer those totals first.\n\n"
        f"User question: {user_query or 'Not provided'}\n"
        f"Deterministic merchant totals (from parser): {merchant_total_text}\n\n"
        f"Statement text preview:\n{ingestion.text_preview}\n"
    )

    try:
        completion = _advisor.client.chat.completions.create(
            model=_advisor.model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON only. Follow this JSON schema exactly:\n"
                        f"{schema_json}"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        response_text = completion.choices[0].message.content if completion.choices else "{}"
        parsed = json.loads(response_text or "{}")

        parsed.setdefault("user_id", user_id)
        parsed.setdefault("session_id", thread_id)
        parsed.setdefault("total_spend_inr", 0)
        parsed.setdefault("categories", [])
        parsed.setdefault("top_cost_drivers", [])
        parsed.setdefault("savings_opportunities", [])
        parsed.setdefault("budget_suggestions", [])
        parsed.setdefault("confidence_score", 0.4)

        report = SpendAnalysisResponse.model_validate(parsed)
        category_sum = sum(item.amount_inr for item in report.categories)
        if report.total_spend_inr <= 0 and category_sum > 0:
            report.total_spend_inr = category_sum

        if report.categories and report.total_spend_inr > 0:
            for item in report.categories:
                item.pct_of_total = round((item.amount_inr / report.total_spend_inr) * 100, 2)

        merchant_lines = [
            f"- {name.title()}: INR {value:,.0f}"
            for name, value in merchant_totals.items()
            if value > 0
        ]
        merchant_answer_section = ""
        if merchants:
            direct_lines = [
                f"- {name.title()}: INR {merchant_totals.get(name, 0.0):,.0f}" for name in merchants
            ]
            requested_total = sum(merchant_totals.get(name, 0.0) for name in merchants)
            merchant_answer_section = (
                "Requested merchant spend totals:\n"
                + "\n".join(direct_lines)
                + f"\nTotal across requested merchants: INR {requested_total:,.0f}\n\n"
            )

        merchant_section = ""
        if merchant_lines:
            merchant_section = "\n\nMerchant spends found:\n" + "\n".join(merchant_lines)
        elif merchants:
            merchant_section = (
                "\n\nMerchant spends found:\n"
                "- No matching merchant transactions were detected in extracted statement text."
            )

        top_cats = report.categories[:3]
        top_cats_text = ", ".join(
            f"{item.category}:{item.amount_inr:.0f}" for item in top_cats
        ) if top_cats else "none"
        merchant_text = ", ".join(
            f"{name}:{value:.0f}" for name, value in merchant_totals.items() if value > 0
        ) or "none"
        summary = (
            f"Spend analysis from statement; total_spend={report.total_spend_inr:.0f}; "
            f"top_categories={top_cats_text}; requested_merchants={merchant_text}"
        )
        _store_statement_analysis_event(
            user_id=user_id,
            thread_id=thread_id,
            event_type="note",
            summary=summary,
        )

        return {
            "success": True,
            "analysis_text": merchant_answer_section + _format_spend_analysis_text(report) + merchant_section,
            "spend_analysis": report.model_dump(mode="json"),
            "merchant_spend_inr": merchant_totals,
            "ingestion": ingestion.model_dump(mode="json"),
        }
    except Exception:
        return {
            "success": True,
            "analysis_text": (
                "I read your statement but need cleaner transaction descriptors for accurate categorization. "
                "Please upload a statement with transaction narration columns visible."
            ),
            "ingestion": ingestion.model_dump(mode="json"),
        }


def chat_with_openai(user_id: str, thread_id: str, message: str) -> str:
    return _advisor.chat(user_id=user_id, thread_id=thread_id, message=message)


def chat_with_adk(user_id: str, thread_id: str, message: str) -> str:
    # Backward compatibility alias.
    return chat_with_openai(user_id=user_id, thread_id=thread_id, message=message)


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

    schema_json = json.dumps(ProfileUpdate.model_json_schema(), ensure_ascii=True)

    try:
        completion = _advisor.client.chat.completions.create(
            model=_advisor.model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract profile updates and return strict JSON only. "
                        "Follow this JSON schema exactly:\n"
                        f"{schema_json}"
                    ),
                },
                {"role": "user", "content": extraction_prompt},
            ],
        )
        response_text = completion.choices[0].message.content if completion.choices else "{}"
        parsed = json.loads(response_text or "{}")
        update = ProfileUpdate.model_validate(parsed)
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
    reply = chat_with_openai(user_id=user_id, thread_id=thread_id, message=user_message)
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
