from music_bot.universal_fallback import download_with_universal_downloader


def test_fallback_is_optional_when_external_package_is_missing(tmp_path) -> None:
    assert download_with_universal_downloader("https://example.invalid/audio", tmp_path) is None
