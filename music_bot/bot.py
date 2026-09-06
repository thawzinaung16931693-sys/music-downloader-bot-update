from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import Config
from .downloader import DownloadError, SearchResult, download_track, extract_url, search_tracks

LOGGER = logging.getLogger(__name__)
HELP_TEXT = (
    "Send a public music link or a keyword search. I will show results for you to choose.\n\n"
    "Commands:\n"
    "/search artist and title\n"
    "/title song title\n"
    "/artist artist name\n\n"
    "You can also send plain text such as: Daft Punk One More Time\n\n"
    "Only download audio you have permission to use."
)
RESULT_COUNT = 5


def create_application(config: Config) -> Application:
    application = Application.builder().token(config.bot_token).build()
    semaphore = asyncio.Semaphore(config.download_workers)

    async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            await update.message.reply_text(HELP_TEXT, disable_web_page_preview=True)

    async def show_search_results(
        update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, field: str
    ) -> None:
        message = update.message
        if not message:
            return
        status = await message.reply_text(f"Searching for {query.strip()}...")
        try:
            results = await asyncio.to_thread(search_tracks, query, field=field)
            context.user_data["search_results"] = results[:RESULT_COUNT]
            context.user_data["search_owner"] = update.effective_user.id if update.effective_user else None
            keyboard = [
                [InlineKeyboardButton(_result_label(index, result), callback_data=f"pick:{index}")]
                for index, result in enumerate(results[:RESULT_COUNT])
            ]
            await status.edit_text(
                "Choose a track to download:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except DownloadError as exc:
            await status.edit_text(str(exc))
        except Exception:
            LOGGER.exception("Unexpected failure while searching for %s", query)
            await status.edit_text("An unexpected error occurred while searching.")

    async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if message:
            await show_search_results(update, context, message.text.partition(" ")[2], "search")

    async def field_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if message:
            command = message.text.partition(" ")[0].lstrip("/").split("@", 1)[0]
            await show_search_results(update, context, message.text.partition(" ")[2], command)

    async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if not message or not message.text:
            return
        url = extract_url(message.text)
        if url:
            await download_url(update, context, url)
        else:
            await show_search_results(update, context, message.text, "search")

    async def pick_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query:
            return
        if query.from_user.id != context.user_data.get("search_owner"):
            await query.answer("Run your own search to choose a result.", show_alert=True)
            return
        await query.answer()
        try:
            index = int((query.data or "").split(":", 1)[1])
            result: SearchResult = context.user_data["search_results"][index]
        except (ValueError, KeyError, IndexError, TypeError):
            await query.edit_message_text("Those search results have expired. Please search again.")
            return
        await query.edit_message_text(f"Downloading: {result.artist} - {result.title}")
        await download_url(update, context, result.url, reply_to=query.message.message_id)

    async def download_url(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        url: str,
        reply_to: int | None = None,
    ) -> None:
        message = update.effective_message
        if not message:
            return
        status = await message.reply_text("Processing your link...")
        try:
            async with semaphore:
                with tempfile.TemporaryDirectory(prefix="music-bot-") as temp_dir:
                    track = await asyncio.to_thread(
                        download_track, url, Path(temp_dir), quality=config.audio_quality,
                        max_duration=config.max_duration_seconds,
                        max_file_size_mb=config.max_file_size_mb, cookies_file=config.cookies_file,
                    )
                    await status.edit_text("Uploading MP3...")
                    await message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
                    with track.path.open("rb") as audio_file:
                        await message.reply_audio(
                            audio=audio_file, title=track.title, performer=track.artist,
                            duration=track.duration or None,
                            caption=f"{track.artist} - {track.title}",
                        )
            await status.delete()
        except DownloadError as exc:
            await status.edit_text(str(exc))
        except Exception:
            LOGGER.exception("Unexpected failure while downloading %s", url)
            await status.edit_text("An unexpected error occurred while downloading.")

    application.add_handler(CommandHandler(["start", "help"], help_handler))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler(["title", "artist"], field_command))
    application.add_handler(CallbackQueryHandler(pick_handler, pattern=r"^pick:\d+$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    return application


def _result_label(index: int, result: SearchResult) -> str:
    duration = f" [{result.duration // 60}:{result.duration % 60:02d}]" if result.duration else ""
    return f"{index + 1}. {result.artist} - {result.title}"[:58] + duration


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    config = Config.from_env()
    LOGGER.info("Starting Telegram Bot API music bot")
    create_application(config).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
