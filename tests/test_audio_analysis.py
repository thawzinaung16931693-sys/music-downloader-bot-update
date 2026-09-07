from music_bot.audio_analysis import ANALYSIS_WINDOW_SECONDS


def test_analysis_window_is_long_enough_for_dj_detection() -> None:
    assert ANALYSIS_WINDOW_SECONDS == 60
