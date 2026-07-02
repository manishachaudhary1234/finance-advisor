from __future__ import annotations

from dataclasses import dataclass, field

from src.schemas.profile import FinancialProfile

from .domain_rules import MINOR_AGE_THRESHOLD, MIN_MINOR_AGE, MINOR_ALLOWED_RISK


@dataclass
class MinorAdvisoryResult:
    is_minor: bool
    guardian_required: bool
    warnings: list[str] = field(default_factory=list)
    recommended_risk_cap: str = MINOR_ALLOWED_RISK


def validate_minor_advisory(profile: FinancialProfile) -> MinorAdvisoryResult:
    age = profile.age

    if age is None:
        return MinorAdvisoryResult(
            is_minor=False,
            guardian_required=False,
            warnings=["Age is missing; cannot determine minor-specific advisory constraints."],
        )

    if age < MIN_MINOR_AGE:
        return MinorAdvisoryResult(
            is_minor=True,
            guardian_required=True,
            warnings=[
                "Age is below configured minimum for this app profile model.",
                "Treat all recommendations as educational only and require guardian supervision.",
            ],
        )

    if age < MINOR_AGE_THRESHOLD:
        warnings = [
            "User is a minor. Recommendations should be educational-first.",
            "Require guardian review before any investment action.",
            f"Restrict risk profile to '{MINOR_ALLOWED_RISK}' unless guardian override is explicitly recorded.",
        ]

        if profile.risk_tolerance and profile.risk_tolerance != MINOR_ALLOWED_RISK:
            warnings.append(
                f"Profile risk_tolerance='{profile.risk_tolerance}' is above allowed minor cap '{MINOR_ALLOWED_RISK}'."
            )

        return MinorAdvisoryResult(
            is_minor=True,
            guardian_required=True,
            warnings=warnings,
        )

    return MinorAdvisoryResult(
        is_minor=False,
        guardian_required=False,
        warnings=[],
    )
