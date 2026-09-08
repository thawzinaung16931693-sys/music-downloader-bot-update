from __future__ import annotations

import ipaddress
import logging
import re
import re
import socket
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import json
from collections.abc import Callable

import yt_dlp
from .provider_capabilities import detect_provider

LOGGER = logging.getLogger(__name__)

SPOTIFY_HOSTS = {"open.spotify.com"}
URL_PATTERN = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
MAX_SEARCH_DURATION_SECONDS = 15 * 60
MAX_SEARCH_RESULTS = 100


class DownloadError(Exception):
    """An error safe to display to a bot user."""


@dataclass(frozen=True)
class DownloadedTrack:
    path: Path
    title: str
    artist: str
    duration: int
    thumbnail: str | None


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str
    artist: str
    duration: int
    thumbnail: str | None = None
    source: str = "YouTube"
    version: str = "Unknown"
    match_score: int = 0


def build_search_url(query: str, *, field: str = "search") -> str:
    query = " ".join(query.split()).strip()
    if not query:
        raise DownloadError(f"Please provide a {field} to search for.")
    if len(query) > 200:
        raise DownloadError("Search text must be 200 characters or fewer.")
    return f"ytsearch{MAX_SEARCH_RESULTS}:{query} audio"


def search_tracks(
    query: str,
    *,
    field: str = "search",
    max_duration: int = MAX_SEARCH_DURATION_SECONDS,
    cookies_file: str | None = None,
    source: str = "youtube",
) -> list[SearchResult]:
    search_url = build_search_url(query, field=field)
    if source == "soundcloud":
        search_url = f"scsearch{MAX_SEARCH_RESULTS}:{query}"
    elif source != "youtube":
        raise DownloadError("That search source is not supported yet.")
    try:
        options: dict[str, object] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "ignoreerrors": True,
            "extract_flat": True,
            "logger": _QuietYtdlpLogger(),
        }
        if cookies_file:
            options["cookiefile"] = cookies_file
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(search_url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError("I could not search for that music right now.") from exc

    results: list[SearchResult] = []
    for entry in info.get("entries", []) if info else []:
        if not entry:
            continue
        video_id = entry.get("id")
        result_url = entry.get("webpage_url") or entry.get("url")
        if not result_url and video_id:
            result_url = f"https://www.youtube.com/watch?v={video_id}"
        if not result_url:
            continue
        duration = int(entry.get("duration") or 0)
        if duration > min(max_duration, MAX_SEARCH_DURATION_SECONDS):
            continue
        results.append(
            SearchResult(
                url=str(result_url),
                title=str(entry.get("title") or "Unknown title"),
                artist=str(entry.get("artist") or entry.get("uploader") or "Unknown artist"),
                duration=duration,
                thumbnail=entry.get("thumbnail"),
                source=str(urlparse(str(result_url)).hostname or "Audio source"),
                version=detect_track_version(str(entry.get("title") or "")),
            )
        )
    if not results:
        raise DownloadError("No public results were found for that search.")
    return rank_search_results(results, query)


def rank_search_results(results: list[SearchResult], query: str) -> list[SearchResult]:
    """Rank provider results for accurate, DJ-oriented search ordering."""
    tokens = _search_tokens(query)
    ranked = [
        replace(result, match_score=round(max(0.0, min(100.0, _result_score(result, tokens)))))
        for result in results
    ]
    ranked.sort(key=lambda result: result.match_score, reverse=True)
    return remove_duplicate_results(ranked)


def explain_match(result: SearchResult) -> str:
    """Return a user-safe explanation of the deterministic match score."""
    if result.match_score >= 80:
        return "Excellent match"
    if result.match_score >= 55:
        return "Strong match"
    if result.match_score >= 30:
        return "Possible match"
    return "Broad match"


def apply_advanced_filters(
    results: list[SearchResult], filters: dict[str, str]
) -> list[SearchResult]:
    """Apply filters locally after broad provider search."""
    filtered = results
    duration = filters.get("duration")
    if duration == "under 5 minutes":
        filtered = [result for result in filtered if 0 < result.duration < 300]
    elif duration == "5 to 10 minutes":
        filtered = [result for result in filtered if 300 <= result.duration <= 600]
    elif duration == "10 to 15 minutes":
        filtered = [result for result in filtered if 600 < result.duration <= 900]

    version = filters.get("version")
    if version:
        filtered = [
            result for result in filtered
            if (
                result.version
                if result.version not in {"", "Unknown", "Original/Unknown"}
                else detect_track_version(result.title)
            ).casefold()
            == version.casefold()
        ]
    return filtered


def detect_track_version(title: str) -> str:
    """Classify common DJ versions from provider title metadata."""
    normalized = title.casefold()
    labels = (
        ("Acapella", ("acapella", "a cappella", "vocal only")),
        ("Instrumental", ("instrumental", "instr")),
        ("Extended Mix", ("extended mix", "extended")),
        ("Club Mix", ("club mix", "club edit")),
        ("Radio Edit", ("radio edit", "radio version")),
        ("Remix", ("remix", "rework", "refix")),
        ("Bootleg", ("bootleg", "edit")),
        ("Mashup", ("mashup", "mash up")),
        ("Live", ("live", "concert")),
        ("DJ Intro", ("dj intro", "intro edit")),
        ("DJ Outro", ("dj outro", "outro edit")),
        ("Original Mix", ("original mix", "original version")),
    )
    for label, terms in labels:
        if any(term in normalized for term in terms):
            return label
    return "Original/Unknown"


def remove_duplicate_results(results: list[SearchResult]) -> list[SearchResult]:
    """Remove duplicate uploads while preserving distinct mixes and live versions."""
    unique: list[SearchResult] = []
    seen: set[tuple[str, str, str]] = set()
    for result in results:
        key = _duplicate_key(result)
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return unique


def _duplicate_key(result: SearchResult) -> tuple[str, str, str]:
    title = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", result.title.casefold())
    title = re.sub(r"\b(official|audio|video|hd|hq|lyrics?|visualizer|4k)\b", " ", title)
    version = ""
    for tag in ("extended mix", "club mix", "original mix", "remix", "instrumental", "acapella", "live"):
        if tag in result.title.casefold():
            version = tag
            break
    normalize = lambda value: re.sub(r"[^a-z0-9]+", "", value.casefold())
    return normalize(result.artist), normalize(title), version


def _search_tokens(query: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w']+", query.casefold())
        if len(token) > 1 and token not in {"audio", "music", "song"}
    }


def _result_score(result: SearchResult, tokens: set[str]) -> float:
    title = result.title.casefold()
    artist = result.artist.casefold()
    haystack = f"{title} {artist}"
    matched = sum(token in haystack for token in tokens)
    score = matched * 10.0
    if tokens and all(token in haystack for token in tokens):
        score += 25.0
    if tokens and all(token in title for token in tokens):
        score += 12.0
    if "official audio" in title or "audio" in title:
        score += 8.0
    if any(tag in title for tag in ("extended mix", "club mix", "original mix", "remix")):
        score += 5.0
    if any(tag in title for tag in ("official video", "live", "shorts", "teaser", "cover")):
        score -= 8.0
    if result.duration:
        score += 2.0
    if {"myanmar", "burmese"} & tokens:
        regional_terms = ("myanmar", "burmese", "မြန်မာ", "yangon", "mandalay")
        score += 40.0 if any(term in haystack for term in regional_terms) else -35.0
    return score


class _QuietYtdlpLogger:
    def debug(self, message: str) -> None:
        return

    def warning(self, message: str) -> None:
        return

    def error(self, message: str) -> None:
        LOGGER.debug("yt-dlp search candidate skipped: %s", message)


def extract_url(text: str) -> str | None:
    match = URL_PATTERN.search(text)
    return match.group(0).rstrip(".,);]}") if match else None


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise DownloadError("Please send a valid http or https music link.")
    if parsed.username or parsed.password:
        raise DownloadError("Links containing credentials are not supported.")

    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, None)}
    except socket.gaierror as exc:
        raise DownloadError("That link's host could not be resolved.") from exc

    if any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise DownloadError("Local or private network links are not supported.")


def download_track(
    url: str,
    output_dir: Path,
    *,
    quality: int,
    max_duration: int,
    max_file_size_mb: int,
    cookies_file: str | None = None,
    progress_callback: Callable[[dict[str, object]], None] | None = None,
) -> DownloadedTrack:
    if not url.startswith("ytsearch"):
        validate_public_url(url)
    from .providers.bandcamp import validate_bandcamp_track_url
    validate_bandcamp_track_url(url)
    from .providers.audius import validate_audius_track_url
    validate_audius_track_url(url)
    from .providers.hearthis import validate_hearthis_track_url
    validate_hearthis_track_url(url)
    from .providers.jamendo import validate_jamendo_track_url
    validate_jamendo_track_url(url)
    from .providers.fma import validate_fma_track_url
    validate_fma_track_url(url)
    from .providers.archive import validate_archive_audio_url
    validate_archive_audio_url(url)
    from .providers.ccmixter import validate_ccmixter_track_url
    validate_ccmixter_track_url(url)
    target = _spotify_search(url, cookies_file) if _is_spotify_url(url) else url
    output_template = str(output_dir / "%(title).180B-%(id)s.%(ext)s")
    options: dict[str, object] = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "max_filesize": max_file_size_mb * 1024 * 1024,
        "socket_timeout": 30,
        "retries": 3,
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        "logger": _QuietYtdlpLogger(),
        "writethumbnail": True,
        "progress_hooks": [progress_callback] if progress_callback else [],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(quality),
            },
            {"key": "FFmpegMetadata", "add_metadata": True},
            {"key": "EmbedThumbnail"},
        ],
    }
    if cookies_file:
        options["cookiefile"] = cookies_file

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(target, download=False)
            if info.get("_type") == "playlist":
                info = next((entry for entry in info.get("entries", []) if entry), None)
            if not info:
                raise DownloadError("No track was found for that link.")

            duration = int(info.get("duration") or 0)
            if duration and duration > max_duration:
                raise DownloadError(
                    f"This track is too long. The limit is {max_duration // 60} minutes."
                )

            info = ydl.extract_info(info.get("webpage_url") or target, download=True)
            prepared_path = Path(ydl.prepare_filename(info))
    except DownloadError as exc:
        if not _is_spotify_url(url) and "too long" not in str(exc).lower():
            from .universal_fallback import download_with_universal_downloader

            fallback_path = download_with_universal_downloader(
                url, output_dir, cookies_file=cookies_file, max_duration=max_duration
            )
            if fallback_path:
                return DownloadedTrack(
                    path=fallback_path,
                    title=fallback_path.stem,
                    artist="Unknown artist",
                    duration=0,
                    thumbnail=None,
                )
        raise
    except yt_dlp.utils.DownloadError as exc:
        message = str(exc).removeprefix("ERROR: ").strip()
        provider = detect_provider(url)
        provider_name = provider.label if provider else "this provider"
        if "Sign in to confirm" in message or "not available" in message:
            raise DownloadError(
                f"{provider_name} rejected or hid this result. Please choose another result "
                "or try a permitted link from another source."
            ) from exc
        if not _is_spotify_url(url):
            from .universal_fallback import download_with_universal_downloader

            fallback_path = download_with_universal_downloader(
                url, output_dir, cookies_file=cookies_file, max_duration=max_duration
            )
            if fallback_path:
                return DownloadedTrack(
                    path=fallback_path,
                    title=fallback_path.stem,
                    artist="Unknown artist",
                    duration=0,
                    thumbnail=None,
                )
        raise DownloadError(f"{provider_name} download failed: {message[:350]}") from exc

    mp3_path = prepared_path.with_suffix(".mp3")
    if not mp3_path.is_file():
        matches = list(output_dir.glob("*.mp3"))
        if len(matches) != 1:
            raise DownloadError("The audio conversion did not produce an MP3 file.")
        mp3_path = matches[0]

    if mp3_path.stat().st_size > max_file_size_mb * 1024 * 1024:
        raise DownloadError(f"The converted file exceeds the {max_file_size_mb} MB limit.")

    return DownloadedTrack(
        path=mp3_path,
        title=str(info.get("track") or info.get("title") or "Unknown title"),
        artist=str(info.get("artist") or info.get("uploader") or "Unknown artist"),
        duration=int(info.get("duration") or 0),
        thumbnail=info.get("thumbnail"),
    )


def _is_spotify_url(url: str) -> bool:
    return (urlparse(url).hostname or "").lower() in SPOTIFY_HOSTS


def _spotify_search(url: str, cookies_file: str | None) -> str:
    del cookies_file
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    if len(path_parts) < 2 or path_parts[0] != "track":
        raise DownloadError("Spotify playlists and albums are not supported; send one track.")

    endpoint = f"https://open.spotify.com/oembed?url={quote(url, safe='')}"
    try:
        request = Request(endpoint, headers={"User-Agent": "telegram-music-bot/0.1"})
        with urlopen(request, timeout=15) as response:
            info = json.load(response)
    except (OSError, ValueError) as exc:
        raise DownloadError(
            "Spotify metadata could not be read. Try a SoundCloud or YouTube link instead."
        ) from exc

    title = info.get("title")
    if not title:
        raise DownloadError("Spotify did not return enough metadata for this track.")
    return f"ytsearch1:{title} audio"
