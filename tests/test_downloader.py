import pytest

from music_bot.downloader import (
    DownloadError,
    _is_spotify_url,
    _spotify_search,
    build_search_url,
    extract_url,
    validate_public_url,
    search_tracks,
    rank_search_results,
    remove_duplicate_results,
)
from unittest.mock import patch


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
        "ytsearch100:Daft Punk One More Time audio"
    )


def test_build_search_url_rejects_empty_query() -> None:
    with pytest.raises(DownloadError, match="provide a title"):
        build_search_url(" ", field="title")


def test_search_filters_long_and_unknown_duration_results() -> None:
    entries = [
        {"webpage_url": "https://example.com/long", "title": "Long", "duration": 901},
        {"webpage_url": "https://example.com/unknown", "title": "Unknown"},
        {"webpage_url": "https://example.com/short", "title": "Short", "duration": 900},
    ]
    fake_info = {"entries": entries}
    with patch("music_bot.downloader.yt_dlp.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = fake_info
        results = search_tracks("test")
    assert [result.title for result in results] == ["Unknown", "Short"]


def test_search_builds_video_url_from_flat_result_id() -> None:
    fake_info = {"entries": [{"id": "abc123", "title": "Short", "duration": 120}]}
    with patch("music_bot.downloader.yt_dlp.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = fake_info
        result = search_tracks("test")[0]
    assert result.url == "https://www.youtube.com/watch?v=abc123"


def test_rank_search_results_prefers_exact_audio_result() -> None:
    from music_bot.downloader import SearchResult

    results = [
        SearchResult("live", "Daft Punk - One More Time (Live)", "Daft Punk", 240),
        SearchResult("audio", "Daft Punk - One More Time (Official Audio)", "Daft Punk", 230),
        SearchResult("other", "One More Time", "Someone Else", 200),
    ]
    assert rank_search_results(results, "Daft Punk One More Time")[0].url == "audio"


def test_duplicate_detection_preserves_distinct_versions() -> None:
    from music_bot.downloader import SearchResult

    results = [
        SearchResult("one", "Artist - Track (Official Audio)", "Artist", 200),
        SearchResult("two", "Artist - Track [HD Video]", "Artist", 200),
        SearchResult("three", "Artist - Track (Extended Mix)", "Artist", 400),
    ]
    unique = remove_duplicate_results(results)
    assert [result.url for result in unique] == ["one", "three"]


def test_soundcloud_search_uses_soundcloud_extractor() -> None:
    with patch("music_bot.downloader.yt_dlp.YoutubeDL") as youtube_dl:
        youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
            "entries": [{"id": "sc1", "title": "House Track", "duration": 180}]
        }
        from music_bot.downloader import search_tracks

        search_tracks("house", source="soundcloud")
        options = youtube_dl.call_args.args[0]
        assert options["noplaylist"] is True


def test_bandcamp_adapter_accepts_track_and_rejects_album() -> None:
    from music_bot.providers.bandcamp import validate_bandcamp_track_url

    validate_bandcamp_track_url("https://artist.bandcamp.com/track/example")
    with pytest.raises(DownloadError, match="one Bandcamp track"):
        validate_bandcamp_track_url("https://artist.bandcamp.com/album/example")
