from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


TrendDirection = Literal["up", "down", "flat"]


class SpendCategory(BaseModel):
    category: str = Field(..., min_length=2, max_length=80)
    amount_inr: float = Field(..., ge=0)
    pct_of_total: float = Field(..., ge=0, le=100)
    trend: TrendDirection = "flat"


class SpendAnalysisResponse(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    total_spend_inr: float = Field(..., ge=0)
    categories: list[SpendCategory] = Field(default_factory=list)
    top_cost_drivers: list[str] = Field(default_factory=list)
    savings_opportunities: list[str] = Field(default_factory=list)
    budget_suggestions: list[str] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0, le=1)

    @model_validator(mode="after")
    def validate_percent_sum(self) -> "SpendAnalysisResponse":
        total_pct = sum(item.pct_of_total for item in self.categories)
        if total_pct > 100.0 + 0.01:
            raise ValueError("Sum of category pct_of_total cannot exceed 100")
        return self
