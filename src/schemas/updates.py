from typing import Optional, Literal
from pydantic import BaseModel,Field

class ProfileUpdate(BaseModel):
    """ Only the fields that change in the profile update are included here. All optional """
    name: Optional[str] = None
    age: Optional[int] = None
    monthly_income_inr: Optional[float] = None
    monthly_expenses_inr: Optional[float] = None
    monthly_emi_inr: Optional[float] = None
    savings_inr: Optional[float] = None 
    new_exclusions : list[str] = Field(default_factory=list)
    primary_goal: Optional[str] = None
    investment_goals: Optional[str] = None
    goal_target_amount_inr : Optional[float] = None
    risk_tolerance: Optional[Literal["low", "medium", "high"]] = None

    should_log_event: bool = False
    event_summary: Optional[str] = None