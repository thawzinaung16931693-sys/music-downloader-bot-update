from music_bot.audio_analysis import _camelot_key
from music_bot.bot import _format_bpm
from music_bot.ai_parser import dj_source_plan, parse_locally


def test_camelot_key_mapping() -> None:
    assert _camelot_key(9, "minor") == "8A"
    assert _camelot_key(0, "major") == "8B"


def test_bpm_is_formatted_to_two_decimal_places() -> None:
    assert _format_bpm(124) == "124.00"
    assert _format_bpm(123.456) == "123.46"
    assert _format_bpm(None) == "unknown"


def test_ai_source_plan_contains_supported_candidates() -> None:
    plan = dj_source_plan(parse_locally("house 124 bpm"))
    assert plan[0].startswith("ytsearch100:")
    assert "scsearch:" in plan[1]
    assert "bcsearch:" in plan[2]
