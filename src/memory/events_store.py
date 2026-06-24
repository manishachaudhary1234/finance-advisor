import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.schemas.events import MemoryEvent

DATA_DIR = Path(__file__).resolve().parents[2]/"data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH= DATA_DIR/"events.db"

def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            source_thread_id TEXT
        )
        """
    )

    conn.commit()


def __get_connection() -> None:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    _init_db(conn)
    return conn

def add_event(event: MemoryEvent) -> None:
    """ Insert one episodic memory event """
    conn = __get_connection()
    try:
        conn.execute(
            """
                INSERT INTO memory_events
                (user_id, event_type, content, created_at, source_thread_id)
                VALUES(?,?,?,?,?)
            """,
            (
                event.user_id,
                event.event_type,
                event.content,
                event.created_at.isoformat(),
                event.source_thread_id
            )
        )
        conn.commit()
    finally:
        conn.close()

def get_recent_events(user_id: str, limit: int=5)->List[MemoryEvent]:
    """ Return most recent events for a user, latest first """
    conn = __get_connection()
    try:
        rows = conn.execute(
            """
                SELECT id, user_id, event_type, content, created_at, source_thread_id
                from memory_events where user_id = ?
                ORDER BY id DESC
                LIMIT ?
            """,
            (user_id,limit)
        ).fetchall()

        events = []

        for row in rows:
            events.append(
                MemoryEvent(
                    id=row[0],
                    user_id=row[1],
                    event_type= row[2],
                    content=row[3],
                    created_at=datetime.fromisoformat(row[4]),
                    source_thread_id=row[5]
                )
            )

        return events
    finally:
        conn.close()