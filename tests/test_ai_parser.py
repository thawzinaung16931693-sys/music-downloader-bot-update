from music_bot.ai_parser import AIParser, parse_locally, provider_query


def test_local_dj_query_parsing() -> None:
    intent = parse_locally("energetic afro house between 120-124 bpm under 10 minutes")
    assert intent.min_bpm == 120
    assert intent.max_bpm == 124
    assert intent.max_duration == 600


def test_parser_falls_back_without_ai_credentials() -> None:
    intent = AIParser(endpoint=None, api_key=None).parse("instrumental piano 128 bpm")
    assert intent.instrumental is True
    assert intent.min_bpm == 128
    assert intent.max_bpm == 128


def test_provider_query_uses_dj_filters() -> None:
    intent = parse_locally("instrumental piano 128 bpm")
    assert provider_query(intent) == "128 bpm instrumental"
