from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDefinition:
    key: str
    label: str
    mode: str
    note: str


SOURCE_CATALOG = (
    SourceDefinition("youtube", "▶️ YouTube", "search", "Keyword search"),
    SourceDefinition("soundcloud", "☁️ SoundCloud", "search", "Keyword search"),
    SourceDefinition("bandcamp", "🎼 Bandcamp", "url", "Public URLs with downloads enabled"),
    SourceDefinition("audius", "🎧 Audius", "url", "Public URLs when available"),
    SourceDefinition("hearthis", "🎚️ HearThis.at", "url", "Public URLs when available"),
    SourceDefinition("jamendo", "📻 Jamendo", "url", "Use according to the track license"),
    SourceDefinition("freemusicarchive", "📦 Free Music Archive", "url", "Use according to the track license"),
    SourceDefinition("archive", "🏛️ Internet Archive", "url", "Public-domain or authorized recordings"),
    SourceDefinition("ccmixter", "🎵 ccMixter", "url", "Creative Commons tracks"),
    SourceDefinition("spotify", "🟢 Spotify metadata", "metadata", "Metadata only"),
    SourceDefinition("beatport", "💿 Beatport metadata", "metadata", "Metadata only unless licensed"),
    SourceDefinition("apple", "🍎 Apple Music metadata", "metadata", "Metadata only"),
    SourceDefinition("deezer", "🎧 Deezer metadata", "metadata", "Metadata only"),
    SourceDefinition("tidal", "🟣 Tidal metadata", "metadata", "Metadata only"),
    SourceDefinition("traxsource", "🎛️ Traxsource metadata", "metadata", "Metadata only unless licensed"),
    SourceDefinition("djuu", "🎚️ DJUU", "url", "Chinese DJ remix tracks"),
    SourceDefinition("172mix", "🎛️ 172Mix", "url", "Chinese DJ remix platform"),
    SourceDefinition("baidudj", "🔊 BaiduDJ", "url", "Login required for download"),
)


def source_definition(key: str) -> SourceDefinition | None:
    return next((source for source in SOURCE_CATALOG if source.key == key), None)
