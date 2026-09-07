from __future__ import annotations

from urllib.parse import urlparse

from ..downloader import DownloadError


def is_fma_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host in {"freemusicarchive.org", "freemusicarchive.com"}


def validate_fma_track_url(url: str) -> None:
    """Accept FMA track pages and reject search, artist, and category pages."""
    if not is_fma_url(url):
        return
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) < 2 or parts[0] not in {"music", "track"}:
        raise DownloadError("Please send one Free Music Archive track URL, not a catalog page.")
