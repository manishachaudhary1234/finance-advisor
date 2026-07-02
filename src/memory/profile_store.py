import sqlite3
import json
from pathlib import Path
from datetime import datetime,timezone
from typing import Optional
import os
from src.schemas.profile import FinancialProfile
from src.schemas.updates import ProfileUpdate

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(exist_ok=True)


def _db_path() -> Path:
    configured = os.getenv("PROFILES_DB_PATH")
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return DATA_DIR / "profiles.db"

def __init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
                 uuid TEXT PRIMARY KEY,
                 data TEXT NOT NULL)
                 """)
    conn.commit()
    

def __get_connection():
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    __init_db(conn)
    return conn

def load_profile(uuid: str) ->Optional[FinancialProfile]:
    """Load profile by user id. Returns None if user has no saved profile yet."""
    conn = __get_connection()
    try:
        row = conn.execute("SELECT data FROM profiles WHERE uuid = ?", (uuid,)).fetchone()
        if row:
            return FinancialProfile.model_validate_json(row[0])
        else:
            return None
    finally:
        conn.close()

def save_profile(profile: FinancialProfile) -> None:
    """ Insert or replace profile for profile.uuid """
    profile.last_updated = datetime.now(timezone.utc)
    payload = profile.model_dump_json()

    conn = __get_connection()

    try:
        conn.execute(
            """ INSERT INTO profiles (uuid,data) VALUES (?,?)
            ON CONFLICT(uuid) DO UPDATE SET data= excluded.data """,
            (profile.uuid, payload)
        )
        conn.commit()
    finally:
        conn.close()


def merge_profile_update(user_id: str, update:ProfileUpdate)->FinancialProfile:
    """ Apply a partial ProfileUpdate onto stored profile, save, and return it """
    profile = load_profile(user_id)
    if profile is None:
        profile = FinancialProfile(uuid=user_id)
    
    #scaler fields: only override when update has a non-None value
    scaler_fields = [
       "name",
        "age",
        "monthly_income_inr",
        "monthly_expenses_inr",
        "monthly_emi_inr",
        "savings_inr",
        "investment_goals",
        "risk_tolerance",
        "primary_goal",
        "goal_target_amount_inr",
    ]

    update_data = update.model_dump(exclude={"new_exclusions","should_log_event","event_summary"})

    for field in scaler_fields:
        value = update_data.get(field)
        if value is not None:
            setattr(profile,field,value)

    #merge exclusions
    if update.new_exclusions:
        existing = profile.excluded_investment_types or []
        seen = {x.lower() for x in existing}
        for item in update.new_exclusions:
            if item.lower() not in seen:
                existing.append(item)
                seen.add(item.lower())
        profile.excluded_investment_types = existing
    
    save_profile(profile)
    return profile


