from __future__ import annotations

import csv
import json
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
        "bpm": analysis.bpm,
        "bpm_confidence": analysis.bpm_confidence,
        "musical_key": analysis.musical_key,
        "key_confidence": analysis.key_confidence,
        "camelot_key": analysis.camelot_key,
        "quality_score": analysis.quality_score,
        "source_bitrate_kbps": analysis.source_bitrate,
        "source_codec": analysis.source_codec,
        "likely_upscaled": analysis.is_likely_upscaled,
        "quality_note": analysis.quality_note,
        "warnings": list(analysis.warnings),
    }


def write_metadata_exports(directory: Path, record: dict[str, object]) -> tuple[Path, Path]:
    json_path = directory / "dj-metadata.json"
    csv_path = directory / "dj-metadata.csv"
    json_path.write_text(json.dumps(record, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(record), extrasaction="ignore")
    writer.writeheader()
    writer.writerow({key: "; ".join(value) if isinstance(value, list) else value for key, value in record.items()})
    csv_path.write_text(buffer.getvalue(), encoding="utf-8")
    return json_path, csv_path
