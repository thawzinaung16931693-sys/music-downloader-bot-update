"""Beatport (beatport.com) — metadata-only provider.

Beatport is the largest DJ music store.  Tracks are sold as paid
downloads; there are no public streaming URLs.  The site uses a
Next.js SPA that does not embed audio file references in the page
HTML.  This provider resolves track metadata (artist, title, BPM,
key, genre, label) from the page or API, but the actual download
must be purchased through the Beatport store.
"""

from __future__ import annotations

from urllib.parse import urlparse

from ..downloader import DownloadError


def is_beatport_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host == "beatport.com"


def validate_beatport_track_url(url: str) -> None:
    if not is_beatport_url(url):
        return
    path = (urlparse(url).path or "").rstrip("/")
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2 or parts[0] != "track":
        raise DownloadError(
            "Please send one Beatport track URL like beatport.com/track/title/123456."
        )