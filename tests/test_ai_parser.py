import asyncio

from music_bot.ai_parser import AIParser, parse_locally, provider_query


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
