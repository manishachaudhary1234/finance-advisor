from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel

class MemoryEvent(BaseModel):
    id: Optional[int] = None #DB auto increment id
    user_id: str
    event_type: Literal[
        "correction",
        "rejection",
        "decision",
        "upload",
        "recommendation",
        "note"
    ]
    content: str
    created_at: datetime 
    source_thread_id: Optional[str] = None