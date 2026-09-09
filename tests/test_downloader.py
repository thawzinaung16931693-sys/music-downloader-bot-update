import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from music_bot.downloader import (
    DownloadedTrack,
    DownloadError,
    _is_spotify_url,
    _spotify_search,
    build_search_url,
    download_track,
    extract_url,
    validate_public_url,
    search_tracks,
    rank_search_results,
    apply_advanced_filters,
    detect_track_version,
    explain_match,
    remove_duplicate_results,
    SearchResult,
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
    assert [result.title for result in results] == ["Short", "Unknown"]


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


def test_rank_search_results_prefers_myanmar_evidence() -> None:
    from music_bot.downloader import SearchResult

    results = [
        SearchResult("foreign", "Popular House Remix", "International Artist", 200),
        SearchResult("myanmar", "Myanmar House Remix", "Burmese DJ", 200),
    ]
    assert rank_search_results(results, "Popular Myanmar House Remix")[0].url == "myanmar"


def test_ranked_result_has_explainable_score() -> None:
    from music_bot.downloader import SearchResult

    result = rank_search_results(
        [SearchResult("a", "Daft Punk One More Time Official Audio", "Daft Punk", 230)],
        "Daft Punk One More Time",
    )[0]
    assert result.match_score > 0
    assert explain_match(result) in {"Excellent match", "Strong match", "Possible match", "Broad match"}


def test_advanced_filters_apply_after_broad_search() -> None:
    from music_bot.downloader import SearchResult

    results = [
        SearchResult("short", "Artist - Track (Extended Mix)", "Artist", 240),
        SearchResult("long", "Artist - Set (Extended Mix)", "Artist", 700),
    ]
    filtered = apply_advanced_filters(results, {"duration": "under 5 minutes", "version": "extended mix"})
    assert [result.url for result in filtered] == ["short"]


def test_advanced_filter_uses_explicit_version_when_available() -> None:
    result = SearchResult("track", "Artist - Track", "Artist", 240, version="Extended Mix")
    assert apply_advanced_filters([result], {"version": "extended mix"}) == [result]


def test_detect_track_version_classifies_dj_edits() -> None:
    assert detect_track_version("Artist - Track (Extended Mix)") == "Extended Mix"
    assert detect_track_version("Artist - Track [Instrumental]") == "Instrumental"
    assert detect_track_version("Artist - Track (Radio Edit)") == "Radio Edit"
    assert detect_track_version("Artist - Track") == "Original/Unknown"


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


def test_audius_adapter_accepts_track_and_rejects_profile() -> None:
    from music_bot.providers.audius import validate_audius_track_url

    validate_audius_track_url("https://audius.co/artist/track-name")
    with pytest.raises(DownloadError, match="one Audius track"):
        validate_audius_track_url("https://audius.co/artist")


def test_hearthis_adapter_accepts_track_and_rejects_discovery() -> None:
    from music_bot.providers.hearthis import validate_hearthis_track_url

    validate_hearthis_track_url("https://hearthis.at/dj/track-name/")
    with pytest.raises(DownloadError, match="one HearThis.at track"):
        validate_hearthis_track_url("https://hearthis.at/discover/")


def test_jamendo_adapter_accepts_track_and_rejects_catalog() -> None:
    from music_bot.providers.jamendo import validate_jamendo_track_url

    validate_jamendo_track_url("https://www.jamendo.com/track/123/name")
    with pytest.raises(DownloadError, match="one Jamendo track"):
        validate_jamendo_track_url("https://www.jamendo.com/artists/")


def test_fma_adapter_accepts_track_and_rejects_catalog() -> None:
    from music_bot.providers.fma import validate_fma_track_url

    validate_fma_track_url("https://freemusicarchive.org/music/Artist/Track/")
    with pytest.raises(DownloadError, match="one Free Music Archive track"):
        validate_fma_track_url("https://freemusicarchive.org/search")


def test_archive_adapter_accepts_item_and_rejects_search() -> None:
    from music_bot.providers.archive import validate_archive_audio_url

    validate_archive_audio_url("https://archive.org/details/example-audio")
    with pytest.raises(DownloadError, match="one Internet Archive audio"):
        validate_archive_audio_url("https://archive.org/search.php?query=music")


def test_ccmixter_adapter_accepts_track_and_rejects_catalog() -> None:
    from music_bot.providers.ccmixter import validate_ccmixter_track_url

    validate_ccmixter_track_url("https://ccmixter.org/files/artist/12345")
    with pytest.raises(DownloadError, match="one ccMixter track"):
        validate_ccmixter_track_url("https://ccmixter.org/search")


# ── download_track: primary (universal) → fallback (yt-dlp) ────────────────


def test_download_track_uses_universal_primary_when_available(tmp_path: Path) -> None:
    """When universal-downloader is present and succeeds, use its result."""
    output_file = tmp_path / "primary-track.mp3"
    output_file.write_bytes(b"primary data")

    with patch(
        "music_bot.downloader._is_spotify_url", return_value=False
    ), patch(
        "music_bot.downloader.validate_public_url"
    ), patch(
        "music_bot.providers.bandcamp.validate_bandcamp_track_url"
    ), patch(
        "music_bot.providers.audius.validate_audius_track_url"
    ), patch(
        "music_bot.providers.hearthis.validate_hearthis_track_url"
    ), patch(
        "music_bot.providers.jamendo.validate_jamendo_track_url"
    ), patch(
        "music_bot.providers.fma.validate_fma_track_url"
    ), patch(
        "music_bot.providers.archive.validate_archive_audio_url"
    ), patch(
        "music_bot.providers.ccmixter.validate_ccmixter_track_url"
    ), patch(
        "music_bot.universal_fallback.download_primary",
        return_value={
            "path": str(output_file),
            "title": "Universal Track",
            "artist": "Universal Artist",
            "duration": 200,
            "thumbnail": "https://img.example.com/u.jpg",
        },
    ):
        result = download_track(
            "https://example.com/track",
            tmp_path,
            quality=192,
            max_duration=900,
            max_file_size_mb=200,
        )

    assert isinstance(result, DownloadedTrack)
    assert result.path == output_file
    assert result.title == "Universal Track"
    assert result.artist == "Universal Artist"
    assert result.duration == 200
    assert result.thumbnail == "https://img.example.com/u.jpg"


def test_download_track_falls_back_to_ytdlp_when_universal_returns_none(tmp_path: Path) -> None:
    """When universal-downloader returns None, fall back to yt-dlp."""
    # Prepare a mock mp3 file for yt-dlp to "produce"
    output_file = tmp_path / "fallback.mp3"
    output_file.write_bytes(b"fallback data")

    mock_info = {
        "title": "Fallback Track",
        "artist": "Fallback Artist",
        "duration": 180,
        "thumbnail": "https://img.example.com/f.jpg",
    }
    fake_ydl = MagicMock()
    fake_ydl.prepare_filename.return_value = str(tmp_path / "fallback")
    fake_ydl.extract_info.side_effect = [mock_info, mock_info]
    fake_ydl_class = MagicMock(return_value=fake_ydl)

    with patch(
        "music_bot.downloader._is_spotify_url", return_value=False
    ), patch(
        "music_bot.downloader.validate_public_url"
    ), patch(
        "music_bot.providers.bandcamp.validate_bandcamp_track_url"
    ), patch(
        "music_bot.providers.audius.validate_audius_track_url"
    ), patch(
        "music_bot.providers.hearthis.validate_hearthis_track_url"
    ), patch(
        "music_bot.providers.jamendo.validate_jamendo_track_url"
    ), patch(
        "music_bot.providers.fma.validate_fma_track_url"
    ), patch(
        "music_bot.providers.archive.validate_archive_audio_url"
    ), patch(
        "music_bot.providers.ccmixter.validate_ccmixter_track_url"
    ), patch(
        "music_bot.universal_fallback.download_primary",
        return_value=None,  # universal unavailable
    ), patch(
        "music_bot.downloader.yt_dlp.YoutubeDL", fake_ydl_class
    ):
        result = download_track(
            "https://example.com/track",
            tmp_path,
            quality=192,
            max_duration=900,
            max_file_size_mb=200,
        )

    assert isinstance(result, DownloadedTrack)
    assert result.title == "Fallback Track"
    assert result.artist == "Fallback Artist"
    assert result.duration == 180
    assert result.thumbnail == "https://img.example.com/f.jpg"


def test_download_track_skips_universal_for_ytsearch_urls(tmp_path: Path) -> None:
    """ytsearch: URLs skip the universal downloader and go straight to yt-dlp."""
    output_file = tmp_path / "ytsearch.mp3"
    output_file.write_bytes(b"ytsearch data")

    mock_info = {
        "title": "Search Result Track",
        "artist": "Search Artist",
        "duration": 150,
        "thumbnail": None,
    }
    fake_ydl = MagicMock()
    fake_ydl.prepare_filename.return_value = str(tmp_path / "ytsearch")
    fake_ydl.extract_info.side_effect = [mock_info, mock_info]
    fake_ydl_class = MagicMock(return_value=fake_ydl)

    universal_called = []

    with patch(
        "music_bot.downloader.validate_public_url"
    ), patch(
        "music_bot.providers.bandcamp.validate_bandcamp_track_url"
    ), patch(
        "music_bot.providers.audius.validate_audius_track_url"
    ), patch(
        "music_bot.providers.hearthis.validate_hearthis_track_url"
    ), patch(
        "music_bot.providers.jamendo.validate_jamendo_track_url"
    ), patch(
        "music_bot.providers.fma.validate_fma_track_url"
    ), patch(
        "music_bot.providers.archive.validate_archive_audio_url"
    ), patch(
        "music_bot.providers.ccmixter.validate_ccmixter_track_url"
    ), patch(
        "music_bot.universal_fallback.download_primary",
        side_effect=lambda *a, **kw: universal_called.append(1) or None,
    ), patch(
        "music_bot.downloader.yt_dlp.YoutubeDL", fake_ydl_class
    ):
        result = download_track(
            "ytsearch1:test query audio",
            tmp_path,
            quality=192,
            max_duration=900,
            max_file_size_mb=200,
        )

    assert isinstance(result, DownloadedTrack)
    assert len(universal_called) == 0  # never called for ytsearch


def test_download_track_universal_primary_preserves_spotify_flow(tmp_path: Path) -> None:
    """Spotify URLs are resolved to ytsearch before universal is attempted."""
    output_file = tmp_path / "spotify-universal.mp3"
    output_file.write_bytes(b"spotify data")

    with patch(
        "music_bot.downloader._is_spotify_url", return_value=True
    ), patch(
        "music_bot.downloader._spotify_search",
        return_value="ytsearch1:Blinding Lights audio",
    ), patch(
        "music_bot.downloader.validate_public_url"
    ), patch(
        "music_bot.providers.bandcamp.validate_bandcamp_track_url"
    ), patch(
        "music_bot.providers.audius.validate_audius_track_url"
    ), patch(
        "music_bot.providers.hearthis.validate_hearthis_track_url"
    ), patch(
        "music_bot.providers.jamendo.validate_jamendo_track_url"
    ), patch(
        "music_bot.providers.fma.validate_fma_track_url"
    ), patch(
        "music_bot.providers.archive.validate_archive_audio_url"
    ), patch(
        "music_bot.providers.ccmixter.validate_ccmixter_track_url"
    ), patch(
        "music_bot.universal_fallback.download_primary",
        return_value={
            "path": str(output_file),
            "title": "Blinding Lights",
            "artist": "The Weeknd",
            "duration": 200,
            "thumbnail": None,
        },
    ):
        result = download_track(
            "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b",
            tmp_path,
            quality=192,
            max_duration=900,
            max_file_size_mb=200,
        )

    assert isinstance(result, DownloadedTrack)
    assert result.title == "Blinding Lights"
    assert result.artist == "The Weeknd"


def test_download_track_ytdlp_fallback_does_not_retry_universal(tmp_path: Path) -> None:
    """When universal fails and yt-dlp also fails, it raises without retry loop."""
    universal_calls = []

    with patch(
        "music_bot.downloader._is_spotify_url", return_value=False
    ), patch(
        "music_bot.downloader.validate_public_url"
    ), patch(
        "music_bot.providers.bandcamp.validate_bandcamp_track_url"
    ), patch(
        "music_bot.providers.audius.validate_audius_track_url"
    ), patch(
        "music_bot.providers.hearthis.validate_hearthis_track_url"
    ), patch(
        "music_bot.providers.jamendo.validate_jamendo_track_url"
    ), patch(
        "music_bot.providers.fma.validate_fma_track_url"
    ), patch(
        "music_bot.providers.archive.validate_archive_audio_url"
    ), patch(
        "music_bot.providers.ccmixter.validate_ccmixter_track_url"
    ), patch(
        "music_bot.universal_fallback.download_primary",
        side_effect=lambda *a, **kw: universal_calls.append(1) or None,
    ), patch(
        "music_bot.downloader.yt_dlp.YoutubeDL",
        side_effect=DownloadError("yt-dlp also failed"),
    ):
        with pytest.raises(DownloadError, match="yt-dlp also failed"):
            download_track(
                "https://example.com/track",
                tmp_path,
                quality=192,
                max_duration=900,
                max_file_size_mb=200,
            )

    assert len(universal_calls) == 1  # tried once, not retried
