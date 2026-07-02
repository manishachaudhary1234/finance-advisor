from __future__ import annotations

from dataclasses import dataclass, field

from src.schemas.recommendation import RecommendationResponse

from .domain_rules import MAX_SINGLE_INSTRUMENT_ALLOCATION_PCT


@dataclass
class OutputValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)


def validate_recommendation_output(payload: RecommendationResponse) -> OutputValidationResult:
    errors: list[str] = []

    total = sum(item.allocation_pct for item in payload.recommendations)
    if total > 100.0 + 0.001:
        errors.append("Total allocation exceeds 100%.")

    for item in payload.recommendations:
        if item.allocation_pct > MAX_SINGLE_INSTRUMENT_ALLOCATION_PCT:
            errors.append(
                f"{item.instrument_name} exceeds max single instrument allocation ({MAX_SINGLE_INSTRUMENT_ALLOCATION_PCT}%)."
            )

    if payload.confidence_score < 0.2:
        errors.append("Confidence score is too low for production recommendation output.")

    return OutputValidationResult(is_valid=(len(errors) == 0), errors=errors)
