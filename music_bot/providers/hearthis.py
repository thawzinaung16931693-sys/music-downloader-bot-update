from __future__ import annotations

from urllib.parse import urlparse

from ..downloader import DownloadError


def is_hearthis_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host == "hearthis.at"


def validate_hearthis_track_url(url: str) -> None:
    """Accept a HearThis.at track path and reject the site home/profile paths."""
    if not is_hearthis_url(url):
        return
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) < 2 or parts[0] in {"discover", "charts", "search"}:
        raise DownloadError("Please send one HearThis.at track URL, not a profile or discovery page.")
