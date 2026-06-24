from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class FinancialProfile(BaseModel):
    uuid: str = Field(..., description="A unique identifier for the user profile")

    name: Optional[str] = Field(None, description="The name of the user")
    age: Optional[int] = Field(None, description="The age of the user")

    monthly_income_inr: Optional[float] = Field(None, description="The monthly income of the user in INR")
    monthly_expenses_inr: Optional[float] = Field(None, description="The monthly expenses of the user in INR")
    monthly_emi_inr : Optional[float] = Field(None, description="The monthly EMI of the user in INR")
    savings_inr: Optional[float] = Field(None, description="The total savings of the user in INR")

    investment_goals: Optional[str] = Field(None, description="The investment goals of the user")
    risk_tolerance: Optional[Literal["low", "medium", "high"]] = Field(None, description="The risk tolerance of the user")

    primary_goal: Optional[Literal["retirement", "education", "wealth_accumulation", "emergency_fund", "other"]] = Field(None, description="The primary financial goal of the user")
    goal_target_amount_inr: Optional[float] = Field(None, description="The target amount for the primary financial goal in INR")
    excluded_investment_types: Optional[list[str]] = Field(None, description="A list of investment types the user wants to exclude from recommendations")

    last_updated: datetime = Field(default_factory=datetime.utcnow, description="The last time the profile was updated")
