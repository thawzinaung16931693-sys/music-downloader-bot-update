from __future__ import annotations

import sqlite3
from pathlib import Path


class Preferences:
    """Persistent per-user settings stored locally on the bot VM."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS user_preferences ("
                "user_id INTEGER PRIMARY KEY, language TEXT NOT NULL DEFAULT 'en', "
                "bitrate INTEGER NOT NULL DEFAULT 320, source TEXT NOT NULL DEFAULT 'youtube')"
            )

    def get(self, user_id: int) -> dict[str, str | int]:
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT language, bitrate, source FROM user_preferences WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return ({"language": row[0], "bitrate": row[1], "source": row[2]} if row else
                {"language": "en", "bitrate": 320, "source": "youtube"})

    def set(self, user_id: int, **values: str | int) -> None:
        settings = self.get(user_id)
        settings.update(values)
        if settings["language"] not in {"en", "my", "zh"}:
            raise ValueError("Unsupported language")
        if settings["bitrate"] not in {128, 192, 256, 320}:
            raise ValueError("Unsupported bitrate")
        if settings["source"] not in {"youtube", "soundcloud"}:
            raise ValueError("Unsupported source")
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO user_preferences(user_id, language, bitrate, source) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET language=excluded.language, bitrate=excluded.bitrate, source=excluded.source",
                (user_id, settings["language"], settings["bitrate"], settings["source"]),
            )
