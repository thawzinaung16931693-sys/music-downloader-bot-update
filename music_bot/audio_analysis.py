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
    bpm, bpm_confidence, musical_key, key_confidence, camelot_key = _analyze_music(path)
    warnings = (f"Source bitrate is only {bitrate} kbps.",) if bitrate and bitrate < 256 else ()
    note = "Source quality appears suitable for DJ use." if not warnings else "Quality may be lower than requested."
    return AudioAnalysis(
        duration, bitrate, sample_rate, audio.get("codec_name"),
        bpm=bpm, bpm_confidence=bpm_confidence, musical_key=musical_key,
        key_confidence=key_confidence, camelot_key=camelot_key,
        quality_note=note, warnings=warnings,
    )


def _analyze_music(path: Path) -> tuple[float | None, float | None, str | None, float | None, str | None]:
    """Estimate tempo and key when optional librosa is installed."""
    try:
        import librosa
        y, sample_rate = librosa.load(path, sr=22_050, mono=True, duration=900)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sample_rate)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sample_rate)
        pitch_class, mode, key_confidence = _estimate_key(chroma.mean(axis=1))
        key = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")[pitch_class]
        musical_key = f"{key} {'minor' if mode == 'minor' else 'major'}"
        camelot = _camelot_key(pitch_class, mode)
        bpm = float(tempo[0] if hasattr(tempo, "__len__") else tempo)
        bpm_confidence = _bpm_confidence(beat_frames, len(y), sample_rate)
        return (bpm if bpm > 0 else None), bpm_confidence, musical_key, key_confidence, camelot
    except (ImportError, OSError, ValueError, RuntimeError):
        return None, None, None, None, None


def _estimate_key(profile) -> tuple[int, str, float]:
    import numpy as np

    major = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    candidates = []
    for pitch_class in range(12):
        candidates.append((float(np.corrcoef(profile, np.roll(major, pitch_class))[0, 1]), pitch_class, "major"))
        candidates.append((float(np.corrcoef(profile, np.roll(minor, pitch_class))[0, 1]), pitch_class, "minor"))
    best = max(candidates)
    confidence = max(0.0, min(1.0, (best[0] + 1) / 2))
    return best[1], best[2], confidence


def _bpm_confidence(beat_frames, sample_count: int, sample_rate: int) -> float:
    if len(beat_frames) < 4 or sample_count / sample_rate < 10:
        return 0.0
    intervals = beat_frames[1:] - beat_frames[:-1]
    variation = float(intervals.std() / intervals.mean()) if intervals.mean() else 1.0
    return max(0.0, min(1.0, 1.0 - variation))


def _camelot_key(pitch_class: int, mode: str) -> str:
    if mode == "minor":
        minor = {8: 1, 3: 2, 10: 3, 5: 4, 0: 5, 7: 6, 2: 7, 9: 8, 4: 9, 11: 10, 6: 11, 1: 12}
        return f"{minor[pitch_class]}A"
    major = {0: 8, 2: 9, 4: 10, 5: 11, 7: 12, 9: 1, 11: 2, 1: 3, 3: 4, 6: 5, 8: 6, 10: 7}
    return f"{major.get(pitch_class, ((pitch_class * 7) % 12) + 1)}B"
