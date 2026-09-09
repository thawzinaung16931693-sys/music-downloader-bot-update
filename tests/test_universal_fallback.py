"""Tests for universal_fallback.py — primary-downloader and legacy fallback paths."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from music_bot.universal_fallback import download_primary, download_with_universal_downloader


# ── download_primary  ──────────────────────────────────────────────────────


def test_primary_returns_none_when_package_missing(tmp_path: Path) -> None:
    with patch.dict(sys.modules, {"downloader": None}):
        result = download_primary("https://example.com/track", tmp_path)
    assert result is None


def test_primary_returns_none_on_import_error(tmp_path: Path) -> None:
    with patch.dict(
        sys.modules,
        {"downloader.core.engines.ytdlp_engine": None},
    ):
        result = download_primary("https://example.com/track", tmp_path)
    assert result is None


def test_primary_returns_none_when_probe_fails(tmp_path: Path) -> None:
    fake_engine = MagicMock()
    fake_engine.probe.side_effect = RuntimeError("probe failed")
    fake_ytdlp = MagicMock(return_value=fake_engine)
    fake_models = MagicMock()
    fake_models.Format.MP3 = "mp3"

    with patch.dict(
        sys.modules,
        {
            "downloader": MagicMock(),
            "downloader.core": MagicMock(),
            "downloader.core.engines": MagicMock(),
            "downloader.core.engines.ytdlp_engine": MagicMock(YtDlpEngine=fake_ytdlp),
            "downloader.core.models": fake_models,
        },
    ):
        result = download_primary("https://example.com/track", tmp_path)
    assert result is None


def test_primary_returns_none_when_too_long(tmp_path: Path) -> None:
    probe_result = MagicMock()
    probe_result.duration = 9999  # exceeds max
    fake_engine = MagicMock()
    fake_engine.probe.return_value = probe_result
    fake_ytdlp = MagicMock(return_value=fake_engine)
    fake_models = MagicMock()
    fake_models.Format.MP3 = "mp3"

    with patch.dict(
        sys.modules,
        {
            "downloader": MagicMock(),
            "downloader.core": MagicMock(),
            "downloader.core.engines": MagicMock(),
            "downloader.core.engines.ytdlp_engine": MagicMock(YtDlpEngine=fake_ytdlp),
            "downloader.core.models": fake_models,
        },
    ):
        result = download_primary("https://example.com/track", tmp_path)
    assert result is None


def test_primary_returns_none_when_download_fails(tmp_path: Path) -> None:
    probe_result = MagicMock()
    probe_result.duration = 180
    fake_engine = MagicMock()
    fake_engine.probe.return_value = probe_result
    fake_engine.download.side_effect = RuntimeError("download failed")
    fake_ytdlp = MagicMock(return_value=fake_engine)
    fake_models = MagicMock()
    fake_models.Format.MP3 = "mp3"

    with patch.dict(
        sys.modules,
        {
            "downloader": MagicMock(),
            "downloader.core": MagicMock(),
            "downloader.core.engines": MagicMock(),
            "downloader.core.engines.ytdlp_engine": MagicMock(YtDlpEngine=fake_ytdlp),
            "downloader.core.models": fake_models,
        },
    ):
        result = download_primary("https://example.com/track", tmp_path)
    assert result is None


def test_primary_returns_none_when_status_not_completed(tmp_path: Path) -> None:
    probe_result = MagicMock()
    probe_result.duration = 180
    download_result = MagicMock()
    download_result.status.value = "failed"
    fake_engine = MagicMock()
    fake_engine.probe.return_value = probe_result
    fake_engine.download.return_value = download_result
    fake_ytdlp = MagicMock(return_value=fake_engine)
    fake_models = MagicMock()
    fake_models.Format.MP3 = "mp3"

    with patch.dict(
        sys.modules,
        {
            "downloader": MagicMock(),
            "downloader.core": MagicMock(),
            "downloader.core.engines": MagicMock(),
            "downloader.core.engines.ytdlp_engine": MagicMock(YtDlpEngine=fake_ytdlp),
            "downloader.core.models": fake_models,
        },
    ):
        result = download_primary("https://example.com/track", tmp_path)
    assert result is None


def test_primary_returns_none_when_output_file_missing(tmp_path: Path) -> None:
    probe_result = MagicMock()
    probe_result.duration = 180
    download_result = MagicMock()
    download_result.status.value = "completed"
    download_result.path = str(tmp_path / "nonexistent.mp3")
    fake_engine = MagicMock()
    fake_engine.probe.return_value = probe_result
    fake_engine.download.return_value = download_result
    fake_ytdlp = MagicMock(return_value=fake_engine)
    fake_models = MagicMock()
    fake_models.Format.MP3 = "mp3"

    with patch.dict(
        sys.modules,
        {
            "downloader": MagicMock(),
            "downloader.core": MagicMock(),
            "downloader.core.engines": MagicMock(),
            "downloader.core.engines.ytdlp_engine": MagicMock(YtDlpEngine=fake_ytdlp),
            "downloader.core.models": fake_models,
        },
    ):
        result = download_primary("https://example.com/track", tmp_path)
    assert result is None


def test_primary_succeeds_with_full_metadata(tmp_path: Path) -> None:
    output_file = tmp_path / "track.mp3"
    output_file.write_bytes(b"fake mp3 data")

    probe_result = MagicMock()
    probe_result.duration = 230
    probe_result.title = "Test Track"
    probe_result.artist = "Test Artist"
    probe_result.thumbnail = "https://img.example.com/thumb.jpg"

    download_result = MagicMock()
    download_result.status.value = "completed"
    download_result.path = str(output_file)

    fake_engine = MagicMock()
    fake_engine.probe.return_value = probe_result
    fake_engine.download.return_value = download_result
    fake_ytdlp = MagicMock(return_value=fake_engine)
    fake_models = MagicMock()
    fake_models.Format.MP3 = "mp3"

    with patch.dict(
        sys.modules,
        {
            "downloader": MagicMock(),
            "downloader.core": MagicMock(),
            "downloader.core.engines": MagicMock(),
            "downloader.core.engines.ytdlp_engine": MagicMock(YtDlpEngine=fake_ytdlp),
            "downloader.core.models": fake_models,
        },
    ):
        result = download_primary("https://example.com/track", tmp_path)

    assert result is not None
    assert result["title"] == "Test Track"
    assert result["artist"] == "Test Artist"
    assert result["duration"] == 230
    assert result["thumbnail"] == "https://img.example.com/thumb.jpg"
    assert result["path"] == str(output_file)


def test_primary_falls_back_to_filename_when_title_missing(tmp_path: Path) -> None:
    output_file = tmp_path / "only-filename.mp3"
    output_file.write_bytes(b"data")

    probe_result = MagicMock()
    probe_result.duration = 120
    probe_result.title = None
    probe_result.artist = None

    download_result = MagicMock()
    download_result.status.value = "completed"
    download_result.path = str(output_file)

    fake_engine = MagicMock()
    fake_engine.probe.return_value = probe_result
    fake_engine.download.return_value = download_result
    fake_ytdlp = MagicMock(return_value=fake_engine)
    fake_models = MagicMock()
    fake_models.Format.MP3 = "mp3"

    with patch.dict(
        sys.modules,
        {
            "downloader": MagicMock(),
            "downloader.core": MagicMock(),
            "downloader.core.engines": MagicMock(),
            "downloader.core.engines.ytdlp_engine": MagicMock(YtDlpEngine=fake_ytdlp),
            "downloader.core.models": fake_models,
        },
    ):
        result = download_primary("https://example.com/track", tmp_path)

    assert result is not None
    assert result["title"] == "only-filename"
    assert result["artist"] == "Unknown artist"


# ── download_with_universal_downloader (legacy) ─────────────────────────────


def test_legacy_fallback_is_optional_when_external_package_is_missing(tmp_path: Path) -> None:
    assert download_with_universal_downloader("https://example.invalid/audio", tmp_path) is None


def test_legacy_returns_path_on_success(tmp_path: Path) -> None:
    output_file = tmp_path / "legacy-track.mp3"
    output_file.write_bytes(b"legacy data")

    probe_result = MagicMock()
    probe_result.duration = 100
    probe_result.title = "Legacy Track"
    probe_result.artist = "Legacy Artist"
    probe_result.thumbnail = None

    download_result = MagicMock()
    download_result.status.value = "completed"
    download_result.path = str(output_file)

    fake_engine = MagicMock()
    fake_engine.probe.return_value = probe_result
    fake_engine.download.return_value = download_result
    fake_ytdlp = MagicMock(return_value=fake_engine)
    fake_models = MagicMock()
    fake_models.Format.MP3 = "mp3"

    with patch.dict(
        sys.modules,
        {
            "downloader": MagicMock(),
            "downloader.core": MagicMock(),
            "downloader.core.engines": MagicMock(),
            "downloader.core.engines.ytdlp_engine": MagicMock(YtDlpEngine=fake_ytdlp),
            "downloader.core.models": fake_models,
        },
    ):
        result = download_with_universal_downloader(
            "https://example.com/track", tmp_path
        )

    assert result is not None
    assert result.is_file()
    assert result == output_file