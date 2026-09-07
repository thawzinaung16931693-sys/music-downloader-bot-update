from __future__ import annotations

import asyncio
from html import escape
import logging
import tempfile
from pathlib import Path

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
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
from .ai_parser import AIParser, provider_query
from .audio_analysis import analyze_audio
from .downloader import DownloadError, SearchResult, download_track, extract_url, search_tracks
from .metadata import enrich_metadata

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
HELP_TEXTS = {
    "en": HELP_TEXT,
    "my": "🎵 <b>Music Finder</b>\n━━━━━━━━━━━━━━━━━━\nသီချင်းအမည်၊ အဆိုတော် သို့မဟုတ် လင့်ခ် ပို့ပြီး MP3 ရယူပါ။\n\n🔎 /search အဆိုတော်နှင့် သီချင်းအမည်\n🎵 /title သီချင်းအမည်\n👤 /artist အဆိုတော်အမည်\n\n⚖️ ခွင့်ပြုချက်ရှိသော အသံဖိုင်များကိုသာ ဒေါင်းလုပ်လုပ်ပါ။",
    "zh": "🎵 <b>Music Finder</b>\n━━━━━━━━━━━━━━━━━━\n发送歌曲名、歌手名或音乐链接，下载高质量 MP3。\n\n🔎 /search 歌手和歌曲名\n🎵 /title 歌曲名\n👤 /artist 歌手名\n\n⚖️ 请只下载您有权使用的音频。",
}
SEARCH_PAGE_SIZE = 5
LANGUAGES = {
    "en": {"name": "English", "search": "Search", "help": "Help", "language": "Language"},
    "my": {"name": "မြန်မာ", "search": "ရှာဖွေရန်", "help": "အကူအညီ", "language": "ဘာသာစကား"},
    "zh": {"name": "中文", "search": "搜索音乐", "help": "帮助", "language": "语言"},
}
BOT_COMMANDS = [
    BotCommand("start", "Start the music bot"),
    BotCommand("help", "Show help and usage"),
    BotCommand("search", "Search by artist and title"),
    BotCommand("title", "Search by song title"),
    BotCommand("artist", "Search by artist name"),
    BotCommand("language", "Choose interface language"),
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
    ai_parser = AIParser()

    async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            await update.message.reply_text(HELP_TEXTS[_language(context)], parse_mode="HTML", disable_web_page_preview=True, reply_markup=_menu(context))

    async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            await update.message.reply_text(
                "🌐 Choose your language / ဘာသာစကား / 语言:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
                    [InlineKeyboardButton("🇲🇲 မြန်မာ", callback_data="lang:my")],
                    [InlineKeyboardButton("🇨🇳 中文", callback_data="lang:zh")],
                ]),
            )

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
            intent = await asyncio.to_thread(ai_parser.parse, query)
            results = await asyncio.to_thread(
                search_tracks,
                provider_query(intent),
                field=field,
                max_duration=min(config.max_duration_seconds, 900),
                cookies_file=config.cookies_file,
            )
            if not results:
                raise DownloadError("No results under 15 minutes were found. Try another keyword.")
            context.user_data["search_results"] = results
            context.user_data["search_owner"] = update.effective_user.id if update.effective_user else None
            first = results[0] if results else None
            if first and first.thumbnail:
                await status.delete()
                preview = await message.reply_photo(first.thumbnail)
                await _show_search_page(preview, context, 0)
            else:
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
        if message.text in {value["help"] for value in LANGUAGES.values()} | {f"❓ {value['help']}" for value in LANGUAGES.values()}:
            await help_handler(update, context)
            return
        if message.text in {value["language"] for value in LANGUAGES.values()} | {f"🌐 {value['language']}" for value in LANGUAGES.values()}:
            await language_handler(update, context)
            return
        if message.text in {value["search"] for value in LANGUAGES.values()} | {f"🔎 {value['search']}" for value in LANGUAGES.values()}:
            await message.reply_text("🔎 Send a song, artist, or music link.", reply_markup=_menu(context))
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
        if query.message.photo:
            await query.edit_message_caption(
                caption=f"⬇️ <b>Preparing download</b>\n{escape(result.artist)} - {escape(result.title)}",
                parse_mode="HTML",
            )
        else:
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

    async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query:
            return
        language = (query.data or "").split(":", 1)[1]
        context.user_data["language"] = language
        await query.answer()
        await query.edit_message_text(f"✅ Language: {LANGUAGES[language]['name']}")
        await query.message.reply_text("🔎 Send a song, artist, or music link.", reply_markup=_menu(context))

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.error("Unhandled Telegram update error", exc_info=context.error)
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("❌ Something went wrong. Please try again.")

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
                    progress = {"percent": -1}

                    def progress_hook(data: dict[str, object]) -> None:
                        if data.get("status") == "downloading":
                            raw = str(data.get("_percent_str", "0")).strip("% ")
                            try:
                                progress["percent"] = int(float(raw))
                            except ValueError:
                                pass

                    download_task = asyncio.create_task(asyncio.to_thread(
                        download_track, url, Path(temp_dir), quality=config.audio_quality,
                        max_duration=config.max_duration_seconds,
                        max_file_size_mb=config.max_file_size_mb, cookies_file=config.cookies_file,
                        progress_callback=progress_hook,
                    ))
                    last_percent = -1
                    while not download_task.done():
                        await asyncio.sleep(2)
                        percent = progress["percent"]
                        if percent >= 0 and percent != last_percent:
                            last_percent = percent
                            blocks = percent // 10
                            await status.edit_text(
                                f"⬇️ <b>Downloading</b>\n{'█' * blocks}{'░' * (10 - blocks)} {percent}%",
                                parse_mode="HTML",
                            )
                    track = await download_task
                    analysis = await asyncio.to_thread(analyze_audio, track.path)
                    await asyncio.to_thread(
                        enrich_metadata,
                        track.path,
                        analysis,
                        title=track.title,
                        artist=track.artist,
                    )
                    await status.edit_text("✅ <b>Track ready</b>\n⬆️ Uploading MP3...", parse_mode="HTML")
                    await message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
                    with track.path.open("rb") as audio_file:
                        await message.reply_audio(
                            audio=audio_file, title=track.title, performer=track.artist,
                            duration=track.duration or None,
                            caption=(
                                f"🎵 {track.artist} - {track.title}\n"
                                f"💿 {analysis.codec or '?'} • {analysis.bitrate or '?'} kbps • "
                                f"⏱ {int(analysis.duration // 60)}:{int(analysis.duration % 60):02d}\n"
                                f"🎧 {analysis.quality_note or 'Quality checked'}"
                            ),
                        )
            await status.delete()
        except DownloadError as exc:
            await status.edit_text(f"⚠️ {escape(str(exc))}", parse_mode="HTML")
        except Exception:
            LOGGER.exception("Unexpected failure while downloading %s", url)
            await status.edit_text("❌ An unexpected error occurred while downloading.")

    application.add_handler(CommandHandler(["start", "help"], help_handler))
    application.add_handler(CommandHandler("language", language_handler))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler(["title", "artist"], field_command))
    application.add_handler(CallbackQueryHandler(pick_handler, pattern=r"^pick:\d+$"))
    application.add_handler(CallbackQueryHandler(next_handler, pattern=r"^next:\d+$"))
    application.add_handler(CallbackQueryHandler(language_callback, pattern=r"^lang:(en|my|zh)$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_error_handler(error_handler)
    return application


async def _show_search_page(message, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    results: list[SearchResult] = context.user_data["search_results"]
    start = page * SEARCH_PAGE_SIZE
    page_results = results[start : start + SEARCH_PAGE_SIZE]
    if not page_results:
        await _edit_result_message(message, "⚠️ There are no more results. Choose a track from the previous page.", None)
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
    await _edit_result_message(
        message,
        f"🎧 <b>Choose a track</b>\nPage {page + 1} of {(len(results) + SEARCH_PAGE_SIZE - 1) // SEARCH_PAGE_SIZE}\n\nTap a result to download:\n<i>🎵 title  •  👤 artist  •  ⏱ duration  •  🌐 source</i>",
        InlineKeyboardMarkup(keyboard),
    )


async def _edit_result_message(message, text: str, markup: InlineKeyboardMarkup | None) -> None:
    if message.photo:
        await message.edit_caption(caption=text, reply_markup=markup, parse_mode="HTML")
    else:
        await message.edit_text(text, reply_markup=markup, parse_mode="HTML")


def _result_label(index: int, result: SearchResult) -> str:
    duration = f" [{result.duration // 60}:{result.duration % 60:02d}]" if result.duration else ""
    label = f"🎵 {index + 1}. {result.artist} - {result.title} · {result.source}"
    return label[:58] + duration


def _language(context: ContextTypes.DEFAULT_TYPE) -> str:
    language = context.user_data.get("language", "en")
    return language if language in HELP_TEXTS else "en"


def _menu(context: ContextTypes.DEFAULT_TYPE) -> ReplyKeyboardMarkup:
    labels = LANGUAGES.get(context.user_data.get("language", "en"), LANGUAGES["en"])
    return ReplyKeyboardMarkup(
        [[f"🔎 {labels['search']}", f"❓ {labels['help']}"], [f"🌐 {labels['language']}"],],
        resize_keyboard=True,
        is_persistent=True,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    config = Config.from_env()
    LOGGER.info("Starting Telegram Bot API music bot")
    create_application(config).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
