"""Tests for DJUU (djuu.com) provider."""
import pytest

from music_bot.downloader import DownloadError
from music_bot.providers.djuu import (
    is_djuu_url,
    validate_djuu_track_url,
    resolve_djuu_audio,
    _PLAY_PAGE,
    _MUSIC_VAR,
    _MUSIC_VAR_ALT,
)


# ── URL detection ──────────────────────────────────────────────────────────


def test_djuu_track_url_detected() -> None:
    assert is_djuu_url("https://www.djuu.com/play/322569.html")
    assert is_djuu_url("https://djuu.com/play/123.html")
    assert not is_djuu_url("https://www.djuu.com.example.org/play/123.html")
    assert not is_djuu_url("https://soundcloud.com/djuu/track")


# ── Validation ─────────────────────────────────────────────────────────────


def test_validate_accepts_play_url() -> None:
    validate_djuu_track_url("https://www.djuu.com/play/322569.html")
    validate_djuu_track_url("https://djuu.com/play/1.html")


def test_validate_rejects_category_url() -> None:
    with pytest.raises(DownloadError, match="one DJUU track"):
        validate_djuu_track_url("https://www.djuu.com/djlist/4_1.html")


def test_validate_rejects_search_url() -> None:
    with pytest.raises(DownloadError, match="one DJUU track"):
        validate_djuu_track_url("https://www.djuu.com/search?musicname=test")


def test_validate_rejects_root() -> None:
    with pytest.raises(DownloadError, match="one DJUU track"):
        validate_djuu_track_url("https://www.djuu.com/")


def test_validate_non_djuu_passes_through() -> None:
    """Non-DJUU URLs should not raise."""
    validate_djuu_track_url("https://soundcloud.com/artist/track")


# ── Regex patterns ─────────────────────────────────────────────────────────


def test_play_page_regex_matches_normal_url() -> None:
    assert _PLAY_PAGE.match("/play/322569.html")
    assert _PLAY_PAGE.match("/play/1.html")
    assert not _PLAY_PAGE.match("/play/")
    assert not _PLAY_PAGE.match("/play/abc.html")
    assert not _PLAY_PAGE.match("/djlist/4_1.html")


def test_music_var_regex_extracts_file_and_name() -> None:
    snippet = (
        "var music = {id: 322569, type: '4', "
        "name: '刘欢 - 好汉歌(Dj宁 Electro Rmx 2026)', "
        "file: 'c4/22/2026/338f205ccefe6b46', "
        "good: 0, click: 410, next: 322568, pre: 322569}"
    )
    m = _MUSIC_VAR.search(snippet)
    assert m is not None
    assert m.group(1) == "c4/22/2026/338f205ccefe6b46"
    assert m.group(2) == "刘欢 - 好汉歌(Dj宁 Electro Rmx 2026)"


def test_music_var_alt_regex_extracts_reversed_fields() -> None:
    """When name appears before file in the object literal."""
    snippet = (
        "var music = {id: 123, type: '5', "
        "name: 'Artist - Track (Remix)', "
        "file: 'a1/b2/2026/deadbeef', click: 0}"
    )
    m = _MUSIC_VAR_ALT.search(snippet)
    assert m is not None
    assert m.group(1) == "Artist - Track (Remix)"
    assert m.group(2) == "a1/b2/2026/deadbeef"


# ── Resolver tests (mocked HTTP) ───────────────────────────────────────────


def test_resolve_returns_m4a_url_and_title() -> None:
    html = """<html><script>
    var music = {id: 322569, type: '4',
    name: '刘欢 - 好汉歌(Dj宁 Electro Rmx 2026)',
    file: 'c4/22/2026/338f205ccefe6b46', good: 0, click: 410,
    next: 322568, pre: 322569};
    </script></html>"""
    from unittest.mock import patch, MagicMock

    with patch("music_bot.providers.djuu.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = html.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        m4a_url, title = resolve_djuu_audio(
            "https://www.djuu.com/play/322569.html"
        )

    assert m4a_url == "https://mp4.djuu.com/c4/22/2026/338f205ccefe6b46.m4a"
    assert title == "刘欢 - 好汉歌(Dj宁 Electro Rmx 2026)"


def test_resolve_raises_on_missing_file_ref() -> None:
    html = "<html><body>No music object here</body></html>"
    from unittest.mock import patch, MagicMock

    with patch("music_bot.providers.djuu.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = html.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(DownloadError, match="Could not find the audio"):
            resolve_djuu_audio("https://www.djuu.com/play/322569.html")


def test_resolve_raises_on_network_error() -> None:
    from unittest.mock import patch

    with patch("music_bot.providers.djuu.urlopen", side_effect=OSError("timeout")):
        with pytest.raises(DownloadError, match="Could not load"):
            resolve_djuu_audio("https://www.djuu.com/play/322569.html")


def test_resolve_raises_on_bad_url_pattern() -> None:
    with pytest.raises(DownloadError, match="Unrecognised"):
        resolve_djuu_audio("https://www.djuu.com/djlist/4_1.html")


# ── Provider capabilities ──────────────────────────────────────────────────


def test_djuu_in_capabilities() -> None:
    from music_bot.provider_capabilities import detect_provider, ProviderCapability

    provider = detect_provider("https://www.djuu.com/play/322569.html")
    assert provider is not None
    assert provider.key == "djuu"
    assert provider.direct_download is True
    assert provider.metadata_only is False


def test_djuu_in_source_catalog() -> None:
    from music_bot.source_catalog import source_definition

    djuu = source_definition("djuu")
    assert djuu is not None
    assert djuu.label == "🎚️ DJUU"
    assert djuu.mode == "url"


# ── downloader.py _djuu_resolve ────────────────────────────────────────────


def test_djuu_resolve_hook() -> None:
    from music_bot.downloader import _is_djuu_url, _djuu_resolve

    assert _is_djuu_url("https://www.djuu.com/play/322569.html")
    assert not _is_djuu_url("https://soundcloud.com/track")

    html = """<script>
    var music = {id: 99, type: '4',
    name: 'Test Track', file: 'aa/bb/cc', click: 0};
    </script>"""
    from unittest.mock import patch, MagicMock

    with patch("music_bot.providers.djuu.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = html.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        resolved = _djuu_resolve("https://www.djuu.com/play/99.html")

    assert resolved == "https://mp4.djuu.com/aa/bb/cc.m4a"