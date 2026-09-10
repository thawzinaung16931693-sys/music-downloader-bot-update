"""Search history and favorites persistence for AI-assisted searches."""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HistoryEntry:
    """A saved search query with metadata."""
    query: str
    timestamp: float
    user_id: int
    intent_json: str | None = None
    result_count: int = 0
    is_favorite: bool = False


class SearchHistory:
    """Persistent search history and favorites store."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    query TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    intent_json TEXT,
                    result_count INTEGER DEFAULT 0,
                    is_favorite INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON search_history(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON search_history(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_favorite ON search_history(user_id, is_favorite)")
            conn.commit()

    def add(self, user_id: int, query: str, intent=None, result_count: int = 0) -> None:
        """Record a search query."""
        intent_json = None
        if intent:
            try:
                intent_json = json.dumps({
                    "artist": intent.artist,
                    "title": intent.title,
                    "genre": intent.genre,
                    "mood": intent.mood,
                    "language": intent.language,
                    "region": intent.region,
                    "min_bpm": intent.min_bpm,
                    "max_bpm": intent.max_bpm,
                })
            except Exception:
                pass
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO search_history (user_id, query, timestamp, intent_json, result_count) VALUES (?, ?, ?, ?, ?)",
                (user_id, query, time.time(), intent_json, result_count),
            )
            conn.commit()

    def get_recent(self, user_id: int, limit: int = 10) -> list[HistoryEntry]:
        """Get recent searches for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT query, timestamp, user_id, intent_json, result_count, is_favorite "
                "FROM search_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit),
            )
            return [HistoryEntry(*row) for row in cursor.fetchall()]

    def get_favorites(self, user_id: int) -> list[HistoryEntry]:
        """Get user's favorite searches."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT query, timestamp, user_id, intent_json, result_count, is_favorite "
                "FROM search_history WHERE user_id = ? AND is_favorite = 1 ORDER BY timestamp DESC",
                (user_id,),
            )
            return [HistoryEntry(*row) for row in cursor.fetchall()]

    def toggle_favorite(self, user_id: int, query: str) -> bool:
        """Toggle favorite status for the most recent matching query. Returns new status."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT is_favorite FROM search_history WHERE user_id = ? AND query = ? ORDER BY timestamp DESC LIMIT 1",
                (user_id, query),
            )
            row = cursor.fetchone()
            if not row:
                return False
            new_status = 0 if row[0] else 1
            conn.execute(
                "UPDATE search_history SET is_favorite = ? WHERE user_id = ? AND query = ? AND timestamp = ("
                "SELECT MAX(timestamp) FROM search_history WHERE user_id = ? AND query = ?)",
                (new_status, user_id, query, user_id, query),
            )
            conn.commit()
            return bool(new_status)

    def clear_history(self, user_id: int) -> int:
        """Clear non-favorite history for a user. Returns count of deleted entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM search_history WHERE user_id = ? AND is_favorite = 0",
                (user_id,),
            )
            conn.commit()
            return cursor.rowcount
