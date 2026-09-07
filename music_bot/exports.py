from __future__ import annotations

import csv
import json
import re
from io import StringIO
from pathlib import Path

from .dj_models import AudioAnalysis


def metadata_record(*, title: str, artist: str, analysis: AudioAnalysis) -> dict[str, object]:
    return {
        "title": title,
        "artist": artist,
        "duration_seconds": round(analysis.duration, 2),
        "codec": analysis.codec,
        "bitrate_kbps": analysis.bitrate,
        "sample_rate_hz": analysis.sample_rate,
        "bpm": f"{analysis.bpm:.2f}" if analysis.bpm is not None else None,
        "bpm_confidence": round(analysis.bpm_confidence, 3) if analysis.bpm_confidence is not None else None,
        "musical_key": analysis.musical_key,
        "key_confidence": round(analysis.key_confidence, 3) if analysis.key_confidence is not None else None,
        "camelot_key": analysis.camelot_key,
        "quality_score": analysis.quality_score,
        "source_bitrate_kbps": analysis.source_bitrate,
        "source_codec": analysis.source_codec,
        "likely_upscaled": analysis.is_likely_upscaled,
        "quality_note": analysis.quality_note,
        "warnings": list(analysis.warnings),
    }


def write_metadata_exports(
    directory: Path, record: dict[str, object], *, filename_stem: str | None = None
) -> tuple[Path, Path]:
    stem = _safe_stem(filename_stem or f"{record['artist']}-{record['title']}")
    json_path = directory / f"{stem}.json"
    csv_path = directory / f"{stem}.csv"
    json_path.write_text(json.dumps(record, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(record), extrasaction="ignore")
    writer.writeheader()
    writer.writerow({key: "; ".join(value) if isinstance(value, list) else value for key, value in record.items()})
    csv_path.write_text(buffer.getvalue(), encoding="utf-8")
    return json_path, csv_path


def _safe_stem(value: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return (stem or "dj-metadata")[:120]
