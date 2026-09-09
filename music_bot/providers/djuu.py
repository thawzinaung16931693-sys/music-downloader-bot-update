"""DJUU (djuu.com) — Chinese DJ remix provider.

Resolves play-page URLs to publicly streamable M4A audio URLs.
The site uses jPlayer in the browser to stream .m4a files from
``mp4.djuu.com``; these streaming URLs do not require authentication
(unlike the download-endpoint which needs login + U-coins).
"""

from __future__ import annotations

import re
import logging
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..downloader import DownloadError

LOGGER = logging.getLogger(__name__)

# Play pages: /play/322569.html  (numeric ID)
_PLAY_PAGE = re.compile(r"^/play/(\d+)\.html$", re.IGNORECASE)
# Embedded JSON-like object: var music = {id: ..., file: '...', name: '...', ...}
_MUSIC_VAR = re.compile(
    r"var\s+music\s*=\s*\{[^}]*file:\s*'([^']+)'[^}]*name:\s*'([^']+)'",
    re.DOTALL,
)
_MUSIC_VAR_ALT = re.compile(
    r"var\s+music\s*=\s*\{[^}]*name:\s*'([^']+)'[^}]*file:\s*'([^']+)'",
    re.DOTALL,
)

USER_AGENT = "BarLarLarBot/1.0 (telegram-music-bot)"


def is_djuu_url(url: str) -> bool:
    """Check whether a URL belongs to djuu.com."""
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host == "djuu.com"


def validate_djuu_track_url(url: str) -> None:
    """Accept DJUU play-page URLs, reject category/search pages.

    Raises :class:`DownloadError` when the URL does not point to a
    single track page.
    """
    if not is_djuu_url(url):
        return
    path = (urlparse(url).path or "").rstrip("/")
    if not _PLAY_PAGE.match(path):
        raise DownloadError(
            "Please send one DJUU track URL like djuu.com/play/322569.html, "
            "not a category, search, or album page."
        )


def resolve_djuu_audio(url: str) -> tuple[str, str]:
    """Return (m4a_url, track_title) by scraping the play page.

    Raises :class:`DownloadError` when the page cannot be fetched or
    the audio file reference is missing.
    """
    path = (urlparse(url).path or "").rstrip("/")
    match = _PLAY_PAGE.match(path)
    if not match:
        raise DownloadError(f"Unrecognised DJUU URL pattern: {url}")

    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
    except OSError as exc:
        LOGGER.warning("DJUU page fetch failed for %s: %s", url, exc)
        raise DownloadError(
            "Could not load the DJUU page. The site may be unavailable."
        ) from exc

    # Try both field-order variants of the embedded music object
    for pattern in (_MUSIC_VAR, _MUSIC_VAR_ALT):
        m = pattern.search(html)
        if m:
            if pattern is _MUSIC_VAR:
                file_ref, title = m.group(1), m.group(2)
            else:
                title, file_ref = m.group(1), m.group(2)
            break
    else:
        raise DownloadError(
            "Could not find the audio file reference on the DJUU page. "
            "The track may have been removed or the page format changed."
        )

    m4a_url = f"https://mp4.djuu.com/{file_ref}.m4a"
    LOGGER.info("Resolved DJUU track %d → %s", int(match.group(1)), m4a_url)
    return m4a_url, title