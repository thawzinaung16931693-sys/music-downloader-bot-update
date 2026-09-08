import asyncio

import pytest

from music_bot.ai_parser import AIParser, _decode_json_object, _intent_from_values, parse_locally, provider_query


def test_local_dj_query_parsing() -> None:
    intent = parse_locally("energetic afro house between 120-124 bpm under 10 minutes")
    assert intent.min_bpm == 120
    assert intent.max_bpm == 124
    assert intent.max_duration == 600


def test_parser_falls_back_without_ai_credentials() -> None:
    intent = AIParser(endpoint=None, api_key=None).parse("instrumental piano 128 bpm")
    assert intent.used_ai is False
    assert intent.fallback_reason == "not_configured"
    assert intent.intent.instrumental is True
    assert intent.intent.min_bpm == 128
    assert intent.intent.max_bpm == 128


def test_provider_query_uses_dj_filters() -> None:
    intent = parse_locally("instrumental piano 128 bpm")
    assert "instrumental piano 128 bpm" in provider_query(intent)


def test_provider_query_preserves_original_user_keywords() -> None:
    intent = parse_locally("Popular Myanmar House Remix")
    assert "Popular Myanmar House Remix" in provider_query(intent)


def test_myanmar_intent_adds_regional_provider_terms() -> None:
    query = provider_query(parse_locally("Popular Myanmar House Remix"))
    assert "Myanmar" in query
    assert "Burmese" in query
    assert "Myanmar DJ" in query


def test_provider_query_does_not_duplicate_original_terms() -> None:
    intent = _intent_from_values(
        "Popular Myanmar House Remix",
        {"region": "Myanmar", "genre": "House", "keywords": ["Remix", "Myanmar"]},
    )
    query = provider_query(intent)
    assert query.startswith("Popular Myanmar House Remix")
    assert query.split().count("Myanmar") == 1
    assert query.split().count("House") == 1


def test_async_parser_uses_local_fallback_without_credentials() -> None:
    result = asyncio.run(AIParser(endpoint=None, api_key=None).parse_async("house 124 bpm"))
    assert result.used_ai is False
    assert result.fallback_reason == "not_configured"


def test_gemini_endpoint_url_is_supported() -> None:
    import os

    previous = os.environ.get("AI_PROVIDER")
    os.environ["AI_PROVIDER"] = "gemini"
    parser = AIParser(
        endpoint="https://generativelanguage.googleapis.com/v1beta",
        api_key="test",
        model="gemini-flash-latest",
    )
    assert parser.provider == "gemini"
    if previous is None:
        os.environ.pop("AI_PROVIDER", None)
    else:
        os.environ["AI_PROVIDER"] = previous


def test_intent_validation_rejects_invalid_bpm_range() -> None:
    with pytest.raises(ValueError, match="between 40 and 240"):
        _intent_from_values("test", {"min_bpm": 999})
    with pytest.raises(ValueError, match="cannot exceed"):
        _intent_from_values("test", {"min_bpm": 130, "max_bpm": 120})


def test_intent_validation_normalizes_and_limits_fields() -> None:
    intent = _intent_from_values(
        "test", {"artist": "  Vini   Vici ", "max_duration": 5000, "instrumental": True}
    )
    assert intent.artist == "Vini Vici"
    assert intent.max_duration == 900
    assert intent.instrumental is True


def test_json_decoder_accepts_gemini_markdown_fence() -> None:
    assert _decode_json_object("```json\n{\"genre\": \"House\"}\n```")["genre"] == "House"


def test_intent_validation_rejects_invalid_keywords() -> None:
    with pytest.raises(ValueError, match="keywords"):
        _intent_from_values("test", {"keywords": "House"})


def test_intent_validation_accepts_null_optional_duration() -> None:
    intent = _intent_from_values("test", {"max_duration": None})
    assert intent.max_duration == 900


def test_intent_validation_preserves_dj_context_fields() -> None:
    intent = _intent_from_values(
        "Popular Myanmar House Remix",
        {"language": "Burmese", "region": "Myanmar", "version": "Remix", "popularity": "popular"},
    )
    assert intent.language == "Burmese"
    assert intent.region == "Myanmar"
    assert intent.version == "Remix"
    assert "Myanmar" in provider_query(intent)
