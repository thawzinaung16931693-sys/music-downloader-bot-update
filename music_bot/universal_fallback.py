from __future__ import annotations

from pathlib import Path


def download_with_universal_downloader(
    url: str,
    output_dir: Path,
    *,
    cookies_file: str | None = None,
    max_duration: int = 900,
) -> Path | None:
    """Use vmexe/universal-downloader's headless yt-dlp engine as an optional fallback."""
    try:
        from downloader.core.engines.ytdlp_engine import YtDlpEngine
        from downloader.core.models import DownloadRequest, Format
    except ImportError:
        return None

    try:
        engine = YtDlpEngine()
        info = engine.probe(url, cookies=cookies_file)
        if info.duration and info.duration > max_duration:
            return None
        result = engine.download(
            DownloadRequest(url=url, out_dir=output_dir, fmt=Format.MP3, audio_only=True),
            cookies=cookies_file,
        )
    except Exception:
        return None
    if result.status.value != "completed" or not result.path:
        return None
    path = Path(result.path)
    return path if path.is_file() else None
