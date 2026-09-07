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
from .exports import metadata_record, write_metadata_exports
from .source_catalog import SOURCE_CATALOG, source_definition
from .preferences import Preferences

LOGGER = logging.getLogger(__name__)
HELP_TEXT = (
    "🎵 <b>Music Finder</b>\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "Find a track and download it as a high-quality MP3.\n\n"
    "🔎 <b>Search commands</b>\n"
    "• /search artist and title (normal YouTube search)\n"
    "• /aisearch DJ filters (AI-assisted search)\n"
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
    "en": {"name": "English", "search": "Search", "ai_search": "AI Search", "help": "Help", "language": "Language"},
    "my": {"name": "မြန်မာ", "search": "ရှာဖွေရန်", "ai_search": "AI ရှာဖွေရန်", "help": "အကူအညီ", "language": "ဘာသာစကား"},
    "zh": {"name": "中文", "search": "搜索音乐", "ai_search": "AI 搜索", "help": "帮助", "language": "语言"},
}
BOT_COMMANDS = [
    BotCommand("start", "Start the music bot"),
    BotCommand("help", "Show help and usage"),
    BotCommand("search", "Search by artist and title"),
    BotCommand("aisearch", "AI-assisted DJ source search"),
    BotCommand("title", "Search by song title"),
    BotCommand("artist", "Search by artist name"),
    BotCommand("language", "Choose interface language"),
    BotCommand("menu", "Show the music keyboard"),
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
    preferences = Preferences(Path("runtime/preferences.db"))

    async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            await update.message.reply_text(HELP_TEXTS[_language(context)], parse_mode="HTML", disable_web_page_preview=True, reply_markup=_menu(context))

    async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            await update.message.reply_text("🎛️ Music controls are ready below.", reply_markup=_menu(context))

    async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message and update.effective_user:
            await update.message.reply_text(
                _settings_text(preferences.get(update.effective_user.id)),
                parse_mode="HTML",
                reply_markup=_settings_markup(),
            )

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
        update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, field: str, use_ai: bool = False
    ) -> None:
        message = update.message
        if not message:
            return
        status = await message.reply_text(
            f"🔎 <b>Searching</b>\n<code>{escape(query.strip())}</code>\n\n⏳ Finding the best matches...",
            parse_mode="HTML",
        )
        try:
            parsed = await asyncio.to_thread(ai_parser.parse, query) if use_ai else None
            intent = parsed.intent if parsed else None
            if use_ai and parsed:
                if parsed.used_ai:
                    await status.edit_text("🤖 AI understood your DJ request. Searching matching tracks...")
                else:
                    reason = "timed out" if parsed.fallback_reason == "timeout" else "is unavailable"
                    await status.edit_text(f"⚠️ AI {reason}. Using local DJ parsing instead...")
            results = await asyncio.to_thread(
                search_tracks,
                provider_query(intent) if intent else query,
                field=field,
                max_duration=min(config.max_duration_seconds, 900),
                cookies_file=config.cookies_file,
                source=(
                    preferences.get(update.effective_user.id)["source"]
                    if update.effective_user
                    else "youtube"
                ),
            )
            if not results:
                raise DownloadError("No results under 15 minutes were found. Try another keyword.")
            context.user_data["search_results"] = results
            context.user_data["search_query"] = query
            context.user_data["search_field"] = field
            context.user_data["search_use_ai"] = use_ai
            context.user_data["search_source"] = "youtube"
            if update.effective_user:
                context.user_data["search_source"] = preferences.get(update.effective_user.id)["source"]
            context.user_data["search_genre"] = None
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

    async def run_filtered_search(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        source: str | None = None,
        genre: str | None = None,
    ) -> None:
        message = update.effective_message
        if not message:
            return
        base_query = context.user_data.get("search_query", "")
        query = " ".join(part for part in (base_query, genre) if part)
        selected_source = source or context.user_data.get("search_source", "youtube")
        status = await message.reply_text(f"🔎 Searching {selected_source} for {escape(query)}...")
        try:
            search_query = query
            if context.user_data.get("search_use_ai"):
                intent_result = await asyncio.to_thread(ai_parser.parse, query)
                search_query = provider_query(intent_result.intent)
            results = await asyncio.to_thread(
                search_tracks,
                search_query,
                field="search",
                max_duration=min(config.max_duration_seconds, 900),
                cookies_file=config.cookies_file,
                source=selected_source,
            )
            context.user_data["search_results"] = results
            context.user_data["search_source"] = selected_source
            context.user_data["search_query"] = query
            if genre is not None:
                context.user_data["search_genre"] = genre
            await _show_search_page(status, context, 0)
        except DownloadError as exc:
            await status.edit_text(f"⚠️ {escape(str(exc))}")

    async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if message:
            context.user_data["ai_search_mode"] = False
            await show_search_results(update, context, message.text.partition(" ")[2], "search")

    async def ai_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if message:
            context.user_data["ai_search_mode"] = False
            await show_search_results(update, context, message.text.partition(" ")[2], "search", True)

    async def field_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if message:
            command = message.text.partition(" ")[0].lstrip("/").split("@", 1)[0]
            await show_search_results(update, context, message.text.partition(" ")[2], command)

    async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if not message or not message.text:
            return
        if context.user_data.pop("custom_genre_mode", False):
            await run_filtered_search(update, context, genre=message.text.strip())
            return
        if message.text in {value["help"] for value in LANGUAGES.values()} | {f"❓ {value['help']}" for value in LANGUAGES.values()}:
            await help_handler(update, context)
            return
        if message.text in {value["language"] for value in LANGUAGES.values()} | {f"🌐 {value['language']}" for value in LANGUAGES.values()}:
            await language_handler(update, context)
            return
        if message.text in {value["search"] for value in LANGUAGES.values()} | {f"🔎 {value['search']}" for value in LANGUAGES.values()}:
            context.user_data["ai_search_mode"] = False
            await message.reply_text("🔎 Send a song, artist, or music link.", reply_markup=_menu(context))
            return
        if message.text in {value["ai_search"] for value in LANGUAGES.values()} | {f"🤖 {value['ai_search']}" for value in LANGUAGES.values()}:
            context.user_data["ai_search_mode"] = True
            await message.reply_text("🤖 Describe your DJ search, for example: energetic house between 120-124 bpm", reply_markup=_menu(context))
            return
        if message.text == "⚙️ Settings":
            await settings_handler(update, context)
            return
        url = extract_url(message.text)
        if url:
            context.user_data["ai_search_mode"] = False
            await download_url(update, context, url)
        else:
            use_ai = bool(context.user_data.pop("ai_search_mode", False))
            await show_search_results(update, context, message.text, "search", use_ai)

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
        preferences.set(query.from_user.id, language=language)
        await query.answer()
        await query.edit_message_text(f"✅ Language: {LANGUAGES[language]['name']}")
        await query.message.reply_text("🔎 Send a song, artist, or music link.", reply_markup=_menu(context))

    async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query:
            return
        action = (query.data or "").split(":", 1)[1]
        if action == "back":
            await query.answer()
            await query.edit_message_text(_settings_text(preferences.get(query.from_user.id)), parse_mode="HTML", reply_markup=_settings_markup())
            return
        await query.answer()
        options = [128, 192, 256, 320] if action == "bitrate" else ["youtube", "soundcloud"]
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{value}{' kbps' if action == 'bitrate' else ''}", callback_data=f"set:{action}:{value}")]
            for value in options
        ] + [[InlineKeyboardButton("↩️ Back", callback_data="settings:back")]]))

    async def setting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query:
            kind, value = (query.data or "").split(":", 2)[1:]
            preferences.set(query.from_user.id, **{kind: int(value) if kind == "bitrate" else value})
            await query.answer("Setting saved")
            await query.edit_message_text(_settings_text(preferences.get(query.from_user.id)), parse_mode="HTML", reply_markup=_settings_markup())

    async def filter_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or query.from_user.id != context.user_data.get("search_owner"):
            return
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Source", callback_data="filter:source")],
            [InlineKeyboardButton("🎚️ Genre", callback_data="filter:genre")],
            [InlineKeyboardButton("↩️ Back to results", callback_data="filter:back")],
        ]))

    async def filter_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or query.from_user.id != context.user_data.get("search_owner"):
            return
        choice = (query.data or "").split(":", 1)[1]
        await query.answer()
        if choice == "source":
            searchable = [source for source in SOURCE_CATALOG if source.mode == "search"]
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
                *[[InlineKeyboardButton(source.label, callback_data=f"source:{source.key}")] for source in searchable],
                [InlineKeyboardButton("🔗 Other direct URLs", callback_data="filter:urls")],
                [InlineKeyboardButton("ℹ️ Metadata-only sources", callback_data="filter:metadata")],
                [InlineKeyboardButton("↩️ Back", callback_data="filter:panel")],
            ]))
        elif choice == "urls":
            url_sources = [source for source in SOURCE_CATALOG if source.mode == "url"]
            await query.edit_message_text(
                "🔗 Send a public URL from one of these sources. The owner must permit downloads:\n\n"
                + "\n".join(f"{source.label} • {source.note}" for source in url_sources),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="filter:panel")]]),
            )
        elif choice == "metadata":
            metadata_sources = [source.label for source in SOURCE_CATALOG if source.mode == "metadata"]
            await query.edit_message_text(
                "ℹ️ These services provide metadata only. Audio downloads require official or licensed access:\n\n"
                + "\n".join(metadata_sources),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="filter:panel")]]),
            )
        elif choice == "genre":
            genres = ["D&B", "House", "Vinahouse", "Bounce", "Dubstep", "SpeedHouse", "Custom"]
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🎵 {genre}", callback_data=f"genre:{genre}")]
                for genre in genres
            ] + [[InlineKeyboardButton("↩️ Back", callback_data="filter:panel")]]))
        elif choice == "panel":
            await filter_panel_handler(update, context)
        elif choice == "back":
            await _show_search_page(query.message, context, 0)

    async def source_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or query.from_user.id != context.user_data.get("search_owner"):
            return
        source = (query.data or "").split(":", 1)[1]
        definition = source_definition(source)
        if not definition or definition.mode != "search":
            await query.answer("Use a public URL for this source; keyword search is not enabled yet.", show_alert=True)
            return
        await query.answer()
        await run_filtered_search(update, context, source=source)

    async def genre_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or query.from_user.id != context.user_data.get("search_owner"):
            return
        genre = (query.data or "").split(":", 1)[1]
        await query.answer()
        if genre == "Custom":
            context.user_data["custom_genre_mode"] = True
            await query.edit_message_text("🎚️ Send your custom genre, for example: liquid drum and bass")
            return
        await run_filtered_search(update, context, genre=genre)

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
                        download_track, url, Path(temp_dir), quality=int(preferences.get(update.effective_user.id)["bitrate"]) if update.effective_user else config.audio_quality,
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
                    record = metadata_record(title=track.title, artist=track.artist, analysis=analysis)
                    json_path, csv_path = await asyncio.to_thread(
                        write_metadata_exports,
                        Path(temp_dir),
                        record,
                        filename_stem=f"{track.artist}-{track.title}-dj-metadata",
                    )
                    await status.edit_text("✅ <b>Track ready</b>\n⬆️ Uploading MP3...", parse_mode="HTML")
                    await message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
                    with track.path.open("rb") as audio_file:
                        await message.reply_audio(
                            audio=audio_file, title=track.title, performer=track.artist,
                            duration=track.duration or None,
                            caption=_analysis_caption(track.artist, track.title, analysis),
                        )
                    with json_path.open("rb") as json_file:
                        await message.reply_document(json_file, caption="📋 DJ metadata (JSON)")
                    with csv_path.open("rb") as csv_file:
                        await message.reply_document(csv_file, caption="📊 DJ metadata (CSV)")
            await status.delete()
        except DownloadError as exc:
            await status.edit_text(f"⚠️ {escape(str(exc))}", parse_mode="HTML")
        except Exception:
            LOGGER.exception("Unexpected failure while downloading %s", url)
            await status.edit_text("❌ An unexpected error occurred while downloading.")

    application.add_handler(CommandHandler(["start", "help"], help_handler))
    application.add_handler(CommandHandler("language", language_handler))
    application.add_handler(CommandHandler("menu", menu_handler))
    application.add_handler(CommandHandler("settings", settings_handler))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("aisearch", ai_search_command))
    application.add_handler(CommandHandler(["title", "artist"], field_command))
    application.add_handler(CallbackQueryHandler(pick_handler, pattern=r"^pick:\d+$"))
    application.add_handler(CallbackQueryHandler(next_handler, pattern=r"^next:\d+$"))
    application.add_handler(CallbackQueryHandler(language_callback, pattern=r"^lang:(en|my|zh)$"))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^settings:(bitrate|source|back)$"))
    application.add_handler(CallbackQueryHandler(setting_callback, pattern=r"^set:(bitrate|source):.+$"))
    application.add_handler(CallbackQueryHandler(filter_panel_handler, pattern=r"^filters$"))
    application.add_handler(CallbackQueryHandler(filter_choice_handler, pattern=r"^filter:(source|genre|urls|metadata|panel|back)$"))
    application.add_handler(CallbackQueryHandler(source_handler, pattern=r"^source:(youtube|soundcloud)$"))
    application.add_handler(CallbackQueryHandler(genre_handler, pattern=r"^genre:(D&B|House|Vinahouse|Bounce|Dubstep|SpeedHouse|Custom)$"))
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
    keyboard.append([InlineKeyboardButton("⚙️ Filters", callback_data="filters")])
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


def _analysis_caption(artist: str, title: str, analysis) -> str:
    confidence = ""
    if analysis.bpm_confidence is not None and analysis.key_confidence is not None:
        confidence = f"🎯 Confidence: BPM {analysis.bpm_confidence:.0%} • Key {analysis.key_confidence:.0%}\n"
    return (
        f"🎵 {artist} - {title}\n"
        f"💿 {analysis.codec or '?'} • {analysis.bitrate or '?'} kbps • "
        f"⏱ {int(analysis.duration // 60)}:{int(analysis.duration % 60):02d}\n"
        f"🥁 BPM: {_format_bpm(analysis.bpm)} • 🎼 Key: {analysis.musical_key or 'unknown'} • "
        f"🎚️ Camelot: {analysis.camelot_key or 'unknown'}\n"
        f"📊 Quality score: {analysis.quality_score if analysis.quality_score is not None else '?'} / 100\n"
        f"{'⚠️ ' + ' '.join(analysis.warnings) if analysis.warnings else '✅ No quality warnings'}\n"
        f"{confidence}🎧 {analysis.quality_note or 'Quality checked'}"
    )


def _format_bpm(bpm: float | None) -> str:
    return f"{bpm:.2f}" if bpm is not None else "unknown"


def _language(context: ContextTypes.DEFAULT_TYPE) -> str:
    language = context.user_data.get("language", "en")
    return language if language in HELP_TEXTS else "en"


def _menu(context: ContextTypes.DEFAULT_TYPE) -> ReplyKeyboardMarkup:
    labels = LANGUAGES.get(context.user_data.get("language", "en"), LANGUAGES["en"])
    return ReplyKeyboardMarkup(
        [[f"🔎 {labels['search']}", f"🤖 {labels['ai_search']}"], [f"❓ {labels['help']}", "⚙️ Settings"], [f"🌐 {labels['language']}"],],
        resize_keyboard=True,
        is_persistent=True,
    )


def _settings_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎚️ Bitrate", callback_data="settings:bitrate")],
        [InlineKeyboardButton("🌐 Preferred source", callback_data="settings:source")],
    ])


def _settings_text(settings: dict[str, str | int]) -> str:
    return ("⚙️ <b>Your DJ settings</b>\n\n"
            f"🌐 Language: <code>{settings['language']}</code>\n"
            f"🎚️ Bitrate: <code>{settings['bitrate']} kbps</code>\n"
            f"🔗 Source: <code>{settings['source']}</code>")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    config = Config.from_env()
    LOGGER.info("Starting Telegram Bot API music bot")
    create_application(config).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
