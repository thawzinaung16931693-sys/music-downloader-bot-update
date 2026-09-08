from __future__ import annotations

from urllib.parse import urlparse

from ..downloader import DownloadError


def is_archive_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host in {"archive.org", "ia800000.us"} or host.endswith(".archive.org")


def validate_archive_audio_url(url: str) -> None:
    """Accept an Archive.org item/file URL and reject search/navigation pages."""
    if not is_archive_url(url):
        return
    path = urlparse(url).path.strip("/")
    if not path or path.split("/", 1)[0] in {"search", "search.php", "advancedsearch.php"}:
        raise DownloadError("Please send one Internet Archive audio item or file URL.")
    if path.startswith("details/") and len(path.split("/", 1)[1]) == 0:
        raise DownloadError("Please send one Internet Archive audio item or file URL.")
