from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ProviderCapability:
    key: str
    label: str
    keyword_search: bool
    direct_download: bool
    metadata_only: bool = False


CAPABILITIES = {
    "youtube": ProviderCapability("youtube", "YouTube", True, True),
    "soundcloud": ProviderCapability("soundcloud", "SoundCloud", True, True),
    "bandcamp": ProviderCapability("bandcamp", "Bandcamp", False, True),
    "audius": ProviderCapability("audius", "Audius", False, True),
    "hearthis": ProviderCapability("hearthis", "HearThis.at", False, True),
    "jamendo": ProviderCapability("jamendo", "Jamendo", False, True),
    "freemusicarchive": ProviderCapability("freemusicarchive", "Free Music Archive", False, True),
    "archive": ProviderCapability("archive", "Internet Archive", False, True),
    "ccmixter": ProviderCapability("ccmixter", "ccMixter", False, True),
    "spotify": ProviderCapability("spotify", "Spotify", False, False, True),
    "apple": ProviderCapability("apple", "Apple Music", False, False, True),
    "deezer": ProviderCapability("deezer", "Deezer", False, False, True),
    "tidal": ProviderCapability("tidal", "Tidal", False, False, True),
    "beatport": ProviderCapability("beatport", "Beatport", False, False, True),
    "traxsource": ProviderCapability("traxsource", "Traxsource", False, False, True),
}


def detect_provider(url: str) -> ProviderCapability | None:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    rules = {
        "youtube.com": "youtube", "youtu.be": "youtube", "soundcloud.com": "soundcloud",
        "bandcamp.com": "bandcamp", "audius.co": "audius", "hearthis.at": "hearthis",
        "jamendo.com": "jamendo", "freemusicarchive.org": "freemusicarchive",
        "archive.org": "archive", "ccmixter.org": "ccmixter", "spotify.com": "spotify",
        "apple.com": "apple", "deezer.com": "deezer", "tidal.com": "tidal",
        "beatport.com": "beatport", "traxsource.com": "traxsource",
    }
    for domain, key in rules.items():
        if host == domain or host.endswith("." + domain):
            return CAPABILITIES[key]
    return None
