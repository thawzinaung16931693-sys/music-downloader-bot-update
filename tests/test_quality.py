from music_bot.dj_models import AudioAnalysis


def test_quality_fields_are_available() -> None:
    analysis = AudioAnalysis(180, 320, 44100, "mp3", quality_score=85, is_likely_upscaled=True)
    assert analysis.quality_score == 85
    assert analysis.is_likely_upscaled is True
