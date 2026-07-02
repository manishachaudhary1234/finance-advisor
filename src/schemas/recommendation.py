from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


RiskLevel = Literal["low", "medium", "high"]
InstrumentType = Literal["mutual_fund", "etf", "bond", "fd", "gold", "other"]


class InstrumentRecommendation(BaseModel):
    instrument_name: str = Field(..., min_length=2, max_length=120)
    instrument_type: InstrumentType
    allocation_pct: float = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    rationale: str = Field(..., min_length=10, max_length=1200)
    expected_return_pct_min: float | None = Field(default=None, ge=-100, le=200)
    expected_return_pct_max: float | None = Field(default=None, ge=-100, le=200)

    @model_validator(mode="after")
    def validate_return_bounds(self) -> "InstrumentRecommendation":
        if (
            self.expected_return_pct_min is not None
            and self.expected_return_pct_max is not None
            and self.expected_return_pct_min > self.expected_return_pct_max
        ):
            raise ValueError("expected_return_pct_min cannot be greater than expected_return_pct_max")
        return self


class RecommendationResponse(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    recommendations: list[InstrumentRecommendation] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    rebalancing_triggers: list[str] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0, le=1)
    next_review_date: date | None = None

    @model_validator(mode="after")
    def validate_total_allocation(self) -> "RecommendationResponse":
        total = sum(item.allocation_pct for item in self.recommendations)
        if total > 100.0 + 0.001:
            raise ValueError("Total recommended allocation cannot exceed 100%")
        return self
