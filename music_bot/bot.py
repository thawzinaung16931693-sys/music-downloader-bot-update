from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import Config
from .downloader import DownloadError, download_track, extract_url

LOGGER = logging.getLogger(__name__)
HELP_TEXT = (
    "Send me a public music link and I will return a high-quality MP3.\n\n"
    "Search commands:\n"
    "/search artist and title\n"
    "/title song title\n"
    "/artist artist name\n\n"
    "Supported links depend on yt-dlp and commonly include SoundCloud, YouTube, "
    "Bandcamp, and many other sites. Spotify track links are matched by artist and "
    "title to another audio source; Spotify audio itself is not downloaded.\n\n"
    "Only download audio you have permission to use."
)


def create_application(config: Config) -> Application:
    application = Application.builder().token(config.bot_token).build()
    semaphore = asyncio.Semaphore(config.download_workers)

    async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            await update.message.reply_text(HELP_TEXT, disable_web_page_preview=True)

    async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if not message or not message.text:
            return

        url = extract_url(message.text)
        if not url:
            await message.reply_text("Please send a public music link. Use /help for details.")
            return

        status = await message.reply_text("Processing your link...")
        try:
            async with semaphore:
                with tempfile.TemporaryDirectory(prefix="music-bot-") as temp_dir:
                    track = await asyncio.to_thread(
                        download_track,
                        url,
                        Path(temp_dir),
                        quality=config.audio_quality,
                        max_duration=config.max_duration_seconds,
                        max_file_size_mb=config.max_file_size_mb,
                        cookies_file=config.cookies_file,
                    )
                    await status.edit_text("Uploading MP3...")
                    await message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
                    with track.path.open("rb") as audio_file:
                        await message.reply_audio(
                            audio=audio_file,
                            title=track.title,
                            performer=track.artist,
                            duration=track.duration or None,
                            caption=f"{track.artist} - {track.title}",
                        )
            await status.delete()
        except DownloadError as exc:
            await status.edit_text(str(exc), disable_web_page_preview=True)
        except Exception:
            LOGGER.exception("Unexpected failure while processing %s", url)
            await status.edit_text("An unexpected error occurred while processing this link.")

    async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if not message:
            return
        command = message.text.partition(" ")[0].lstrip("/").split("@", 1)[0]
        query = message.text.partition(" ")[2]
        try:
            from .downloader import build_search_url

            search_url = build_search_url(query, field=command)
        except DownloadError as exc:
            await message.reply_text(str(exc))
            return

        status = await message.reply_text(f"Searching for {query.strip()}...")
        try:
            async with semaphore:
                with tempfile.TemporaryDirectory(prefix="music-bot-") as temp_dir:
                    track = await asyncio.to_thread(
                        download_track,
                        search_url,
                        Path(temp_dir),
                        quality=config.audio_quality,
                        max_duration=config.max_duration_seconds,
                        max_file_size_mb=config.max_file_size_mb,
                        cookies_file=config.cookies_file,
                    )
                    await status.edit_text("Uploading MP3...")
                    await message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
                    with track.path.open("rb") as audio_file:
                        await message.reply_audio(
                            audio=audio_file,
                            title=track.title,
                            performer=track.artist,
                            duration=track.duration or None,
                            caption=f"{track.artist} - {track.title}",
                        )
            await status.delete()
        except DownloadError as exc:
            await status.edit_text(str(exc))
        except Exception:
            LOGGER.exception("Unexpected failure while searching for %s", query)
            await status.edit_text("An unexpected error occurred while searching.")

    application.add_handler(CommandHandler(["start", "help"], help_handler))
    application.add_handler(CommandHandler(["search", "title", "artist"], search_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))
    return application


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = Config.from_env()
    LOGGER.info("Starting Telegram Bot API music bot")
    create_application(config).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
