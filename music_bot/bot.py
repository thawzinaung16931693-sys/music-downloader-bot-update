from __future__ import annotations

import asyncio
from html import escape
import logging
import tempfile
from pathlib import Path

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
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
    "🎵 <b>Music Finder</b>\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "Find a track and download it as a high-quality MP3.\n\n"
    "🔎 <b>Search commands</b>\n"
    "• /search artist and title\n"
    "• /title song title\n"
    "• /artist artist name\n\n"
    "💬 Or send plain text, for example:\n"
    "<code>Daft Punk One More Time</code>\n\n"
    "🔗 Public SoundCloud, YouTube, Bandcamp, and other supported links also work.\n\n"
    "⚖️ Download only audio you have permission to use."
)
SEARCH_PAGE_SIZE = 5
BOT_COMMANDS = [
    BotCommand("start", "Start the music bot"),
    BotCommand("help", "Show help and usage"),
    BotCommand("search", "Search by artist and title"),
    BotCommand("title", "Search by song title"),
    BotCommand("artist", "Search by artist name"),
]


def create_application(config: Config) -> Application:
    async def configure_command_menu(application: Application) -> None:
        await application.bot.set_my_commands(BOT_COMMANDS)
        LOGGER.info("Telegram command menu configured")

    application = (
        Application.builder()
        .token(config.bot_token)
        .post_init(configure_command_menu)
        .build()
    )
    semaphore = asyncio.Semaphore(config.download_workers)

    async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            await update.message.reply_text(HELP_TEXT, parse_mode="HTML", disable_web_page_preview=True)

    async def show_search_results(
        update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, field: str
    ) -> None:
        message = update.message
        if not message:
            return
        status = await message.reply_text(
            f"🔎 <b>Searching</b>\n<code>{escape(query.strip())}</code>\n\n⏳ Finding the best matches...",
            parse_mode="HTML",
        )
        try:
            results = await asyncio.to_thread(search_tracks, query, field=field)
            context.user_data["search_results"] = results
            context.user_data["search_owner"] = update.effective_user.id if update.effective_user else None
            await _show_search_page(status, context, 0)
        except DownloadError as exc:
            await status.edit_text(f"⚠️ {escape(str(exc))}", parse_mode="HTML")
        except Exception:
            LOGGER.exception("Unexpected failure while searching for %s", query)
            await status.edit_text("❌ An unexpected error occurred while searching.")

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
        await query.edit_message_text(
            f"⬇️ <b>Preparing download</b>\n{escape(result.artist)} - {escape(result.title)}",
            parse_mode="HTML",
        )
        await download_url(update, context, result.url, reply_to=query.message.message_id)

    async def next_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query:
            return
        if query.from_user.id != context.user_data.get("search_owner"):
            await query.answer("Run your own search to browse results.", show_alert=True)
            return
        try:
            page = int((query.data or "").split(":", 1)[1])
            await query.answer()
            await _show_search_page(query.message, context, page)
        except (ValueError, KeyError, TypeError):
            await query.answer("Those search results have expired.", show_alert=True)

    async def download_url(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        url: str,
        reply_to: int | None = None,
    ) -> None:
        message = update.effective_message
        if not message:
            return
        status = await message.reply_text(
            "🔗 <b>Processing your link</b>\n⏳ Extracting audio...", parse_mode="HTML"
        )
        try:
            async with semaphore:
                with tempfile.TemporaryDirectory(prefix="music-bot-") as temp_dir:
                    track = await asyncio.to_thread(
                        download_track, url, Path(temp_dir), quality=config.audio_quality,
                        max_duration=config.max_duration_seconds,
                        max_file_size_mb=config.max_file_size_mb, cookies_file=config.cookies_file,
                    )
                    await status.edit_text("✅ <b>Track ready</b>\n⬆️ Uploading MP3...", parse_mode="HTML")
                    await message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
                    with track.path.open("rb") as audio_file:
                        await message.reply_audio(
                            audio=audio_file, title=track.title, performer=track.artist,
                            duration=track.duration or None,
                            caption=f"{track.artist} - {track.title}",
                        )
            await status.delete()
        except DownloadError as exc:
            await status.edit_text(f"⚠️ {escape(str(exc))}", parse_mode="HTML")
        except Exception:
            LOGGER.exception("Unexpected failure while downloading %s", url)
            await status.edit_text("❌ An unexpected error occurred while downloading.")

    application.add_handler(CommandHandler(["start", "help"], help_handler))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler(["title", "artist"], field_command))
    application.add_handler(CallbackQueryHandler(pick_handler, pattern=r"^pick:\d+$"))
    application.add_handler(CallbackQueryHandler(next_handler, pattern=r"^next:\d+$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    return application


async def _show_search_page(message, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    results: list[SearchResult] = context.user_data["search_results"]
    start = page * SEARCH_PAGE_SIZE
    page_results = results[start : start + SEARCH_PAGE_SIZE]
    if not page_results:
        await message.edit_text("⚠️ There are no more results. Choose a track from the previous page.")
        return
    keyboard = [
        [InlineKeyboardButton(_result_label(start + index, result), callback_data=f"pick:{start + index}")]
        for index, result in enumerate(page_results)
    ]
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"next:{page - 1}"))
    if start + SEARCH_PAGE_SIZE < len(results):
        navigation.append(InlineKeyboardButton("Next ➡️", callback_data=f"next:{page + 1}"))
    if navigation:
        keyboard.append(navigation)
    await message.edit_text(
        f"🎧 <b>Choose a track</b>\nPage {page + 1} of {(len(results) + SEARCH_PAGE_SIZE - 1) // SEARCH_PAGE_SIZE}\n\nTap a result to download:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


def _result_label(index: int, result: SearchResult) -> str:
    duration = f" [{result.duration // 60}:{result.duration % 60:02d}]" if result.duration else ""
    label = f"🎵 {index + 1}. {result.artist} - {result.title}"
    return label[:58] + duration


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    config = Config.from_env()
    LOGGER.info("Starting Telegram Bot API music bot")
    create_application(config).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
