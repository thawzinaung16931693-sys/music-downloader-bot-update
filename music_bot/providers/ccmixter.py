from __future__ import annotations

from urllib.parse import urlparse

from ..downloader import DownloadError


def is_ccmixter_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host in {"ccmixter.org", "dig.ccmixter.org"} or host.endswith(".ccmixter.org")


def validate_ccmixter_track_url(url: str) -> None:
    """Accept public ccMixter track pages and reject catalog/navigation URLs."""
    if not is_ccmixter_url(url):
        return
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) < 2 or parts[0] in {"search", "tag", "people", "collections"}:
        raise DownloadError("Please send one ccMixter track URL, not a catalog page.")
