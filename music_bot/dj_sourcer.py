from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from .ai_parser import dj_source_plan
from .dj_models import SearchIntent


@dataclass(frozen=True)
class SourceTool:
    name: str
    executable: str
    available: bool


def available_source_tools() -> list[SourceTool]:
    return [
        SourceTool("yt-dlp", "yt-dlp", shutil.which("yt-dlp") is not None),
        SourceTool("spotdl", "spotdl", shutil.which("spotdl") is not None),
        SourceTool("bandcamp-dl", "bandcamp-dl", shutil.which("bandcamp-dl") is not None),
        SourceTool("ffmpeg", "ffmpeg", shutil.which("ffmpeg") is not None),
    ]


def build_open_claw_plan(intent: SearchIntent) -> list[str]:
    """Return source candidates for the AI-assisted DJ sourcing flow."""
    return dj_source_plan(intent)


def tool_version(executable: str) -> str | None:
    try:
        result = subprocess.run([executable, "--version"], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.splitlines()[0] if result.stdout else None
