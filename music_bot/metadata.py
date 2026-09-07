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
        for frame_id in ("TIT2", "TPE1", "TALB", "TBPM", "TKEY", "COMM:DJ Analysis:eng", "TXXX:DJ_CAMELOT"):
            tags.delall(frame_id)
        tags.add(TIT2(encoding=3, text=title))
        tags.add(TPE1(encoding=3, text=artist))
        if album:
            tags.add(TALB(encoding=3, text=album))
        if analysis.bpm:
            tags.add(TBPM(encoding=3, text=f"{analysis.bpm:.2f}"))
        if analysis.musical_key:
            tags.add(TKEY(encoding=3, text=analysis.musical_key))
        if analysis.quality_note:
            tags.add(COMM(encoding=3, lang="eng", desc="DJ Analysis", text=analysis.quality_note))
        if analysis.camelot_key:
            tags.add(TXXX(encoding=3, desc="DJ_CAMELOT", text=analysis.camelot_key))
        if analysis.bpm_confidence is not None:
            tags.add(TXXX(encoding=3, desc="DJ_BPM_CONFIDENCE", text=f"{analysis.bpm_confidence:.3f}"))
        if analysis.key_confidence is not None:
            tags.add(TXXX(encoding=3, desc="DJ_KEY_CONFIDENCE", text=f"{analysis.key_confidence:.3f}"))
        if analysis.quality_score is not None:
            tags.add(TXXX(encoding=3, desc="DJ_QUALITY_SCORE", text=str(analysis.quality_score)))
        if analysis.source_bitrate is not None:
            tags.add(TXXX(encoding=3, desc="DJ_SOURCE_BITRATE", text=f"{analysis.source_bitrate} kbps"))
        if analysis.source_codec:
            tags.add(TXXX(encoding=3, desc="DJ_SOURCE_CODEC", text=analysis.source_codec))
        if analysis.is_likely_upscaled:
            tags.add(TXXX(encoding=3, desc="DJ_QUALITY_WARNING", text="Likely upscaled source"))
        tags.save(path, v2_version=3)
    except (ImportError, OSError):
        pass
    return EnrichedMetadata(title, artist, album, bpm=analysis.bpm, musical_key=analysis.musical_key, camelot_key=analysis.camelot_key)
