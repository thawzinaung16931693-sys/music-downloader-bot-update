import pytest

from music_bot.downloader import (
    DownloadError,
    _is_spotify_url,
    _spotify_search,
    build_search_url,
    extract_url,
    validate_public_url,
)


def test_extract_url_from_message() -> None:
    assert extract_url("Try https://soundcloud.com/user/track.") == (
        "https://soundcloud.com/user/track"
    )


def test_extract_url_returns_none_without_link() -> None:
    assert extract_url("hello bot") is None


def test_private_ip_is_rejected() -> None:
    with pytest.raises(DownloadError, match="private network"):
        validate_public_url("http://127.0.0.1/music")


def test_invalid_scheme_is_rejected() -> None:
    with pytest.raises(DownloadError, match="valid http or https"):
        validate_public_url("file:///music.mp3")


def test_spotify_host_detection_does_not_accept_suffix_attack() -> None:
    assert _is_spotify_url("https://open.spotify.com/track/123")
    assert not _is_spotify_url("https://open.spotify.com.example.org/track/123")


def test_spotify_playlist_is_rejected_without_network_request() -> None:
    with pytest.raises(DownloadError, match="playlists and albums"):
        _spotify_search("https://open.spotify.com/playlist/123", None)


def test_build_search_url_normalizes_query() -> None:
    assert build_search_url("  Daft   Punk   One More Time ") == (
        "ytsearch1:Daft Punk One More Time audio"
    )


def test_build_search_url_rejects_empty_query() -> None:
    with pytest.raises(DownloadError, match="provide a title"):
        build_search_url(" ", field="title")
