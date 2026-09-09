"""172Mix (172mix.com) — Chinese DJ remix provider.

Resolves play-page URLs to publicly streamable M4A audio URLs hosted on
``mp3.172mix.com``.  The page embeds a ``var media`` object whose ``src``
field points to the streaming file; this URL is served without authentication.
"""

from __future__ import annotations

import re
import logging
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..downloader import DownloadError

LOGGER = logging.getLogger(__name__)

_PLAY_PAGE = re.compile(r"^/play/(\d+)$", re.IGNORECASE)
# var media = {..., src: "https://mp3.172mix.com/...m4a", ...};
_MEDIA_VAR = re.compile(
    r"var\s+media\s*=\s*\{[^}]*src:\s*\"([^\"]+)\"[^}]*name:\s*\"([^\"]+)\"",
    re.DOTALL,
)
_MEDIA_VAR_ALT = re.compile(
    r"var\s+media\s*=\s*\{[^}]*name:\s*\"([^\"]+)\"[^}]*src:\s*\"([^\"]+)\"",
    re.DOTALL,
)

USER_AGENT = "BarLarLarBot/1.0 (telegram-music-bot)"


def is_172mix_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host == "172mix.com"


def validate_172mix_track_url(url: str) -> None:
    if not is_172mix_url(url):
        return
    path = (urlparse(url).path or "").rstrip("/")
    if not _PLAY_PAGE.match(path):
        raise DownloadError(
            "Please send one 172Mix track URL like 172mix.com/play/101235, "
            "not a genre, search, or album page."
        )


def resolve_172mix_audio(url: str) -> tuple[str, str]:
    path = (urlparse(url).path or "").rstrip("/")
    match = _PLAY_PAGE.match(path)
    if not match:
        raise DownloadError(f"Unrecognised 172Mix URL pattern: {url}")

    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
    except OSError as exc:
        LOGGER.warning("172Mix page fetch failed for %s: %s", url, exc)
        raise DownloadError("Could not load the 172Mix page.") from exc

    for pattern in (_MEDIA_VAR, _MEDIA_VAR_ALT):
        m = pattern.search(html)
        if m:
            if pattern is _MEDIA_VAR:
                m4a_url, title = m.group(1), m.group(2)
            else:
                title, m4a_url = m.group(1), m.group(2)
            break
    else:
        raise DownloadError(
            "Could not find the audio file reference on the 172Mix page."
        )

    LOGGER.info("Resolved 172Mix track %d → %s", int(match.group(1)), m4a_url)
    return m4a_url, title