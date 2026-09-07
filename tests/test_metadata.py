from music_bot.audio_analysis import _camelot_key


def test_camelot_key_mapping() -> None:
    assert _camelot_key(9, "minor") == "8A"
    assert _camelot_key(0, "major") == "8B"
