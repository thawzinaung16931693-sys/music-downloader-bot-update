from __future__ import annotations

from urllib.parse import urlparse

from ..downloader import DownloadError


def is_jamendo_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host == "jamendo.com" or host.endswith(".jamendo.com")


def validate_jamendo_track_url(url: str) -> None:
    """Accept a public Jamendo track URL and reject catalog/navigation pages."""
    if not is_jamendo_url(url):
        return
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) < 2 or parts[0] not in {"track", "lists"}:
        raise DownloadError("Please send one Jamendo track URL, not a catalog or artist page.")
