"""BaiduDJ (baidudj.com) — metadata-only provider.

BaiduDJ is a commercial DJ music site.  Play pages return 403 to
non-browser user agents and downloads require login + payment (coins).
Until browser-automation or user-supplied cookies are available,
this provider is registered as metadata-only.
"""

from __future__ import annotations

from urllib.parse import urlparse

from ..downloader import DownloadError


def is_baidudj_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host == "baidudj.com"


def validate_baidudj_track_url(url: str) -> None:
    if not is_baidudj_url(url):
        return
    # Accept any track-like URL pattern for now
    path = (urlparse(url).path or "").rstrip("/")
    if not path.startswith("/djmp3/") or len(path) < 8:
        raise DownloadError(
            "Please send one BaiduDJ track URL like baidudj.com/djmp3/362927.html."
        )