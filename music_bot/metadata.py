from __future__ import annotations

from pathlib import Path

from .dj_models import AudioAnalysis, EnrichedMetadata


def enrich_metadata(path: Path, analysis: AudioAnalysis, *, title: str, artist: str, album: str | None = None) -> EnrichedMetadata:
    """Embed available title, artist, album, BPM, key, Camelot, and quality data."""
    try:
        from mutagen.id3 import COMM, ID3, ID3NoHeaderError, TALB, TBPM, TKEY, TIT2, TPE1, TXXX
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = ID3()
        tags[TIT2] = TIT2(encoding=3, text=title)
        tags[TPE1] = TPE1(encoding=3, text=artist)
        if album:
            tags[TALB] = TALB(encoding=3, text=album)
        if analysis.bpm:
            tags[TBPM] = TBPM(encoding=3, text=str(round(analysis.bpm, 2)))
        if analysis.musical_key:
            tags[TKEY] = TKEY(encoding=3, text=analysis.musical_key)
        if analysis.quality_note:
            tags[COMM] = COMM(encoding=3, lang="eng", desc="", text=analysis.quality_note)
        if analysis.camelot_key:
            tags[TXXX] = TXXX(encoding=3, desc="DJ_CAMELOT", text=analysis.camelot_key)
        tags.save(path)
    except (ImportError, OSError):
        pass
    return EnrichedMetadata(title, artist, album, bpm=analysis.bpm, musical_key=analysis.musical_key, camelot_key=analysis.camelot_key)
