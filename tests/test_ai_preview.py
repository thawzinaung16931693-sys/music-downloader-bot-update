from music_bot.bot import _intent_preview
from music_bot.dj_models import SearchIntent


def test_intent_preview_shows_structured_filters() -> None:
    preview = _intent_preview(
        SearchIntent(
            "Popular Myanmar House Remix",
            genre="House",
            min_bpm=120,
            max_bpm=124,
            max_duration=600,
        )
    )
    assert "AI interpretation" in preview
    assert "House" in preview
    assert "120-124" in preview
    assert "10 minutes" in preview
