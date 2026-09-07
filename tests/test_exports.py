import json

from music_bot.dj_models import AudioAnalysis
from music_bot.exports import metadata_record, write_metadata_exports


def test_metadata_exports_include_dj_fields(tmp_path) -> None:
    analysis = AudioAnalysis(
        240, 320, 44100, "mp3", bpm=124, bpm_confidence=0.9,
        musical_key="A minor", key_confidence=0.8, camelot_key="8A", quality_score=95,
    )
    record = metadata_record(title="Track", artist="Artist", analysis=analysis)
    json_path, csv_path = write_metadata_exports(tmp_path, record)
    assert json.loads(json_path.read_text())["camelot_key"] == "8A"
    assert "bpm_confidence" in csv_path.read_text()
