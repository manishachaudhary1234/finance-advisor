from __future__ import annotations

import re
from dataclasses import dataclass, field

from .domain_rules import MAX_QUERY_LENGTH, MIN_QUERY_LENGTH


_INJECTION_PATTERNS = [
    r"ignore\\s+all\\s+previous\\s+instructions",
    r"system\\s+prompt",
    r"developer\\s+message",
    r"jailbreak",
]


@dataclass
class InputValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)


def validate_user_query(query: str) -> InputValidationResult:
    errors: list[str] = []
    cleaned = (query or "").strip()

    if len(cleaned) < MIN_QUERY_LENGTH:
        errors.append(f"Query must be at least {MIN_QUERY_LENGTH} characters long.")
    if len(cleaned) > MAX_QUERY_LENGTH:
        errors.append(f"Query must be at most {MAX_QUERY_LENGTH} characters long.")

    lowered = cleaned.lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            errors.append("Query appears to contain prompt-injection content.")
            break

    return InputValidationResult(is_valid=(len(errors) == 0), errors=errors)
