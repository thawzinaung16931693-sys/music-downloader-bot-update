from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .dj_models import AudioAnalysis


def analyze_audio(path: Path) -> AudioAnalysis:
    """Read technical audio data with FFprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
            check=True, capture_output=True, text=True,
        )
        payload = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise RuntimeError("FFprobe could not inspect this audio file.") from exc
    audio = next((stream for stream in payload.get("streams", []) if stream.get("codec_type") == "audio"), {})
    fmt = payload.get("format", {})
    duration = float(fmt.get("duration") or audio.get("duration") or 0)
    bitrate_raw = audio.get("bit_rate") or fmt.get("bit_rate")
    bitrate = int(bitrate_raw) // 1000 if bitrate_raw else None
    sample_rate = int(audio["sample_rate"]) if audio.get("sample_rate") else None
    warnings = (f"Source bitrate is only {bitrate} kbps.",) if bitrate and bitrate < 256 else ()
    note = "Source quality appears suitable for DJ use." if not warnings else "Quality may be lower than requested."
    return AudioAnalysis(duration, bitrate, sample_rate, audio.get("codec_name"), quality_note=note, warnings=warnings)
