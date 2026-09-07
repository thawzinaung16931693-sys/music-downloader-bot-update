from __future__ import annotations

from urllib.parse import urlparse

from ..downloader import DownloadError


def is_bandcamp_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "bandcamp.com" or host.endswith(".bandcamp.com")


def validate_bandcamp_track_url(url: str) -> None:
    """Reject Bandcamp collection pages; the bot handles one track per request."""
    if not is_bandcamp_url(url):
        return
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) < 2 or parts[0] != "track":
        raise DownloadError("Please send one Bandcamp track URL, not an album or artist page.")
