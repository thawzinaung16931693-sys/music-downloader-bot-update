from music_bot.provider_capabilities import detect_provider


def test_provider_capabilities_are_detected() -> None:
    assert detect_provider("https://youtu.be/example").keyword_search is True
    assert detect_provider("https://open.spotify.com/track/example").metadata_only is True
    assert detect_provider("https://artist.bandcamp.com/track/example").direct_download is True
