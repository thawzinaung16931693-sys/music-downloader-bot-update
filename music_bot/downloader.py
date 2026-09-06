from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import json

import yt_dlp

SPOTIFY_HOSTS = {"open.spotify.com"}
URL_PATTERN = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


class DownloadError(Exception):
    """An error safe to display to a bot user."""


@dataclass(frozen=True)
class DownloadedTrack:
    path: Path
    title: str
    artist: str
    duration: int
    thumbnail: str | None


def build_search_url(query: str, *, field: str = "search") -> str:
    query = " ".join(query.split()).strip()
    if not query:
        raise DownloadError(f"Please provide a {field} to search for.")
    if len(query) > 200:
        raise DownloadError("Search text must be 200 characters or fewer.")
    return f"ytsearch1:{query} audio"


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
) -> DownloadedTrack:
    validate_public_url(url)
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
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(quality),
            },
            {"key": "FFmpegMetadata", "add_metadata": True},
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
    except DownloadError:
        raise
    except yt_dlp.utils.DownloadError as exc:
        message = str(exc).removeprefix("ERROR: ").strip()
        raise DownloadError(f"I could not download this track: {message[:350]}") from exc

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
