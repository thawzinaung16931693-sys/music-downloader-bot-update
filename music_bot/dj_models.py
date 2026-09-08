from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchIntent:
    raw_query: str
    artist: str | None = None
    title: str | None = None
    genre: str | None = None
    mood: str | None = None
    min_bpm: float | None = None
    max_bpm: float | None = None
    max_duration: int = 900
    instrumental: bool | None = None
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class AudioAnalysis:
    duration: float
    bitrate: int | None
    sample_rate: int | None
    codec: str | None
    bpm: float | None = None
    bpm_confidence: float | None = None
    musical_key: str | None = None
    key_confidence: float | None = None
    camelot_key: str | None = None
    energy: float | None = None
    danceability: float | None = None
    quality_note: str | None = None
    quality_score: int | None = None
    source_bitrate: int | None = None
    source_codec: str | None = None
    is_likely_upscaled: bool = False
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EnrichedMetadata:
    title: str
    artist: str
    album: str | None = None
    year: int | None = None
    genre: str | None = None
    artwork_path: str | None = None
    bpm: float | None = None
    musical_key: str | None = None
    camelot_key: str | None = None
