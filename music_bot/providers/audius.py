from __future__ import annotations

from urllib.parse import urlparse

from ..downloader import DownloadError


AUDIO_HOSTS = {"audius.co", "audius.exchange", "audius.disco"}


def is_audius_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host in AUDIO_HOSTS or host.endswith(".audius.co")


def validate_audius_track_url(url: str) -> None:
    """Accept Audius track URLs and reject home/profile pages."""
    if not is_audius_url(url):
        return
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    if len(path_parts) < 2 or path_parts[0] in {"", "discover", "trending"}:
        raise DownloadError("Please send one Audius track URL, not an artist or home page.")
