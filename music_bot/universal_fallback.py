from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


def download_primary(
    url: str,
    output_dir: Path,
    *,
    quality: int = 192,
    cookies_file: str | None = None,
    max_duration: int = 900,
    max_file_size_mb: int = 200,
    progress_callback: Any = None,
) -> dict[str, object] | None:
    """Use vmexe/universal-downloader as the primary download engine.

    Returns a dict with keys ``path``, ``title``, ``artist``, ``duration``,
    ``thumbnail`` when successful, or ``None`` when the engine is unavailable
    or the download fails.
    """
    try:
        from downloader.core.engines.ytdlp_engine import YtDlpEngine
        from downloader.core.models import DownloadRequest, Format, ProbeResult
    except ImportError:
        LOGGER.debug("universal-downloader package not installed; will fall back to yt-dlp")
        return None

    try:
        engine = YtDlpEngine()
        probe: ProbeResult = engine.probe(url, cookies=cookies_file)
    except Exception as exc:
        LOGGER.debug("universal-downloader probe failed for %s: %s", url, exc)
        return None

    if probe.duration and probe.duration > max_duration:
        LOGGER.debug("universal-downloader: track too long (%ds)", probe.duration)
        return None

    try:
        result = engine.download(
            DownloadRequest(
                url=url,
                out_dir=output_dir,
                fmt=Format.MP3,
                audio_only=True,
            ),
            cookies=cookies_file,
            progress_hooks=[progress_callback] if progress_callback else [],
        )
    except Exception as exc:
        LOGGER.debug("universal-downloader download failed for %s: %s", url, exc)
        return None

    if getattr(result, "status", None) is None or str(result.status.value) != "completed":
        LOGGER.debug("universal-downloader: status not completed for %s", url)
        return None
    if not result.path:
        LOGGER.debug("universal-downloader: no output path for %s", url)
        return None

    path = Path(result.path)
    if not path.is_file():
        LOGGER.debug("universal-downloader: output file missing: %s", path)
        return None

    return {
        "path": str(path),
        "title": probe.title or path.stem,
        "artist": probe.artist or "Unknown artist",
        "duration": probe.duration or 0,
        "thumbnail": probe.thumbnail,
    }


def download_with_universal_downloader(
    url: str,
    output_dir: Path,
    *,
    cookies_file: str | None = None,
    max_duration: int = 900,
) -> Path | None:
    """Legacy wrapper kept for backward compatibility.

    Prefer :func:`download_primary` for new call sites.
    """
    result = download_primary(
        url,
        output_dir,
        cookies_file=cookies_file,
        max_duration=max_duration,
    )
    if result is None:
        return None
    path = Path(result["path"])
    return path if path.is_file() else None