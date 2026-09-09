"""Tests for 172Mix, BaiduDJ, and Beatport providers."""
import pytest

from music_bot.downloader import DownloadError


# ── 172Mix ─────────────────────────────────────────────────────────────────


def test_172mix_url_detected() -> None:
    from music_bot.providers._172mix import is_172mix_url

    assert is_172mix_url("https://www.172mix.com/play/101235")
    assert is_172mix_url("https://172mix.com/play/123")
    assert not is_172mix_url("https://172mix.com.example.org/play/123")
    assert not is_172mix_url("https://soundcloud.com/172mix/track")


def test_172mix_validate_accepts_play_url() -> None:
    from music_bot.providers._172mix import validate_172mix_track_url

    validate_172mix_track_url("https://www.172mix.com/play/101235")
    validate_172mix_track_url("https://172mix.com/play/1")


def test_172mix_validate_rejects_genre_url() -> None:
    from music_bot.providers._172mix import validate_172mix_track_url

    with pytest.raises(DownloadError, match="one 172Mix track"):
        validate_172mix_track_url("https://www.172mix.com/genre/gwwq")


def test_172mix_validate_rejects_root() -> None:
    from music_bot.providers._172mix import validate_172mix_track_url

    with pytest.raises(DownloadError, match="one 172Mix track"):
        validate_172mix_track_url("https://www.172mix.com/")


def test_172mix_validate_non_172mix_passes_through() -> None:
    from music_bot.providers._172mix import validate_172mix_track_url

    validate_172mix_track_url("https://soundcloud.com/artist/track")


def test_172mix_resolve_returns_m4a_url_and_title() -> None:
    from music_bot.providers._172mix import resolve_172mix_audio
    from unittest.mock import patch, MagicMock

    html = b"""<script>
    var media = {id: "101235", name: "Kesha - Die Young",
    src: "https://mp3.172mix.com/mp3/userdj/20220825/63074d81db341.m4a"};
    </script>"""

    with patch("music_bot.providers._172mix.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = html
        mock_urlopen.return_value.__enter__.return_value = mock_response

        url, title = resolve_172mix_audio("https://www.172mix.com/play/101235")

    assert url == "https://mp3.172mix.com/mp3/userdj/20220825/63074d81db341.m4a"
    assert title == "Kesha - Die Young"


def test_172mix_resolve_raises_on_missing_media() -> None:
    from music_bot.providers._172mix import resolve_172mix_audio
    from unittest.mock import patch, MagicMock

    with patch("music_bot.providers._172mix.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>No media here</html>"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(DownloadError, match="Could not find"):
            resolve_172mix_audio("https://www.172mix.com/play/101235")


def test_172mix_resolve_raises_on_network_error() -> None:
    from music_bot.providers._172mix import resolve_172mix_audio
    from unittest.mock import patch

    with patch("music_bot.providers._172mix.urlopen", side_effect=OSError("timeout")):
        with pytest.raises(DownloadError, match="Could not load"):
            resolve_172mix_audio("https://www.172mix.com/play/101235")


def test_172mix_in_capabilities() -> None:
    from music_bot.provider_capabilities import detect_provider

    provider = detect_provider("https://www.172mix.com/play/101235")
    assert provider is not None
    assert provider.key == "172mix"
    assert provider.direct_download is True


def test_172mix_in_source_catalog() -> None:
    from music_bot.source_catalog import source_definition

    s = source_definition("172mix")
    assert s is not None
    assert s.mode == "url"


def test_172mix_resolve_hook() -> None:
    from music_bot.downloader import _is_172mix_url, _172mix_resolve

    assert _is_172mix_url("https://www.172mix.com/play/101235")
    assert not _is_172mix_url("https://soundcloud.com/track")

    html = b"""<script>
    var media = {id: "99", name: "Test Track",
    src: "https://mp3.172mix.com/mp3/aa/bb.m4a"};
    </script>"""
    from unittest.mock import patch, MagicMock

    with patch("music_bot.providers._172mix.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = html
        mock_urlopen.return_value.__enter__.return_value = mock_response

        url, title = _172mix_resolve("https://www.172mix.com/play/99")

    assert url == "https://mp3.172mix.com/mp3/aa/bb.m4a"
    assert title == "Test Track"


# ── BaiduDJ ────────────────────────────────────────────────────────────────


def test_baidudj_url_detected() -> None:
    from music_bot.providers._baidudj import is_baidudj_url

    assert is_baidudj_url("https://www.baidudj.com/djmp3/362927.html")
    assert is_baidudj_url("https://baidudj.com/djmp3/123.html")
    assert not is_baidudj_url("https://baidudj.com.example.org/djmp3/123.html")


def test_baidudj_validate_accepts_djmp3_url() -> None:
    from music_bot.providers._baidudj import validate_baidudj_track_url

    validate_baidudj_track_url("https://www.baidudj.com/djmp3/362927.html")


def test_baidudj_validate_rejects_non_track() -> None:
    from music_bot.providers._baidudj import validate_baidudj_track_url

    with pytest.raises(DownloadError, match="one BaiduDJ track"):
        validate_baidudj_track_url("https://www.baidudj.com/sort/c1/0-0-1.html")


def test_baidudj_validate_rejects_root() -> None:
    from music_bot.providers._baidudj import validate_baidudj_track_url

    with pytest.raises(DownloadError, match="one BaiduDJ track"):
        validate_baidudj_track_url("https://www.baidudj.com/")


def test_baidudj_in_capabilities() -> None:
    from music_bot.provider_capabilities import detect_provider

    provider = detect_provider("https://www.baidudj.com/djmp3/362927.html")
    assert provider is not None
    assert provider.key == "baidudj"
    assert provider.metadata_only is True


def test_baidudj_in_source_catalog() -> None:
    from music_bot.source_catalog import source_definition

    s = source_definition("baidudj")
    assert s is not None


# ── Beatport ───────────────────────────────────────────────────────────────


def test_beatport_url_detected() -> None:
    from music_bot.providers._beatport import is_beatport_url

    assert is_beatport_url("https://www.beatport.com/track/blinding-lights/234567")
    assert is_beatport_url("https://beatport.com/track/title/123")
    assert not is_beatport_url("https://beatport.com.example.org/track/123")


def test_beatport_validate_accepts_track_url() -> None:
    from music_bot.providers._beatport import validate_beatport_track_url

    validate_beatport_track_url("https://www.beatport.com/track/title/234567")


def test_beatport_validate_rejects_release_url() -> None:
    from music_bot.providers._beatport import validate_beatport_track_url

    with pytest.raises(DownloadError, match="one Beatport track"):
        validate_beatport_track_url("https://www.beatport.com/release/title/123")


def test_beatport_validate_rejects_artist_url() -> None:
    from music_bot.providers._beatport import validate_beatport_track_url

    with pytest.raises(DownloadError, match="one Beatport track"):
        validate_beatport_track_url("https://www.beatport.com/artist/name/123")


def test_beatport_in_capabilities() -> None:
    from music_bot.provider_capabilities import detect_provider

    provider = detect_provider("https://www.beatport.com/track/title/123")
    assert provider is not None
    assert provider.key == "beatport"
    assert provider.metadata_only is True


def test_beatport_in_source_catalog() -> None:
    from music_bot.source_catalog import source_definition

    s = source_definition("beatport")
    assert s is not None