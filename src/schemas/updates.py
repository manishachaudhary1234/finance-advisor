from typing import Optional, Literal
from pydantic import BaseModel,Field

class ProfileUpdate(BaseModel):
    """ Only the fields that change in the profile update are included here. All optional """
    name: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0, le=120)
    monthly_income_inr: Optional[float] = Field(default=None, ge=0)
    monthly_expenses_inr: Optional[float] = Field(default=None, ge=0)
    monthly_emi_inr: Optional[float] = Field(default=None, ge=0)
    savings_inr: Optional[float] = Field(default=None, ge=0)
    new_exclusions : list[str] = Field(default_factory=list)
    primary_goal: Optional[Literal["retirement", "education", "wealth_accumulation", "emergency_fund", "other"]] = None
    investment_goals: Optional[str] = None
    goal_target_amount_inr : Optional[float] = Field(default=None, ge=0)
    risk_tolerance: Optional[Literal["low", "medium", "high"]] = None

    should_log_event: bool = False
    event_summary: Optional[str] = None