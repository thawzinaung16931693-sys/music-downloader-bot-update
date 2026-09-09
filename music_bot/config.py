from __future__ import annotations

import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    audio_quality: int = 320
    max_duration_seconds: int = 900
    max_file_size_mb: int = 200
    download_workers: int = 2
    cookies_file: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        missing = [
            name
            for name in ("TELEGRAM_BOT_TOKEN",)
            if not os.getenv(name)
        ]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        bot_token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
        if (
            bot_token == "123456789:your_bot_token"
            or not re.fullmatch(r"\d{8,12}:[A-Za-z0-9_-]{30,}", bot_token)
        ):
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is missing or invalid. Create a token with @BotFather."
            )

        quality = _bounded_int("AUDIO_QUALITY", 320, 64, 320)
        if quality not in {128, 192, 256, 320}:
            raise ValueError("AUDIO_QUALITY must be one of: 128, 192, 256, 320")

        return cls(
            bot_token=bot_token,
            audio_quality=quality,
            max_duration_seconds=_bounded_int("MAX_DURATION_SECONDS", 900, 1, 86_400),
            max_file_size_mb=_bounded_int("MAX_FILE_SIZE_MB", 200, 1, 2_000),
            download_workers=_bounded_int("DOWNLOAD_WORKERS", 2, 1, 10),
            cookies_file=os.getenv("COOKIES_FILE") or None,
        )


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = int(os.getenv(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value
