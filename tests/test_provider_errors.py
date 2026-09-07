from music_bot.provider_capabilities import detect_provider


def test_provider_error_context_can_be_named() -> None:
    provider = detect_provider("https://www.youtube.com/watch?v=example")
    assert provider is not None
    assert provider.label == "YouTube"
