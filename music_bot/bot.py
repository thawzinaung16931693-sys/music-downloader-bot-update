from __future__ import annotations

import asyncio
from html import escape
import logging
import subprocess
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
from telegram.request import HTTPXRequest
from telegram.error import NetworkError, RetryAfter, TelegramError

from .config import Config
from .ai_parser import AIParser, provider_query
from .audio_analysis import analyze_audio
from .downloader import DownloadError, SearchResult, apply_advanced_filters, download_track, explain_match, extract_url, search_tracks
from .metadata import enrich_metadata
from .exports import metadata_record, write_metadata_exports
from .source_catalog import SOURCE_CATALOG, source_definition
from .preferences import Preferences
from .provider_capabilities import detect_provider
from .search_history import SearchHistory
from .ui import emoji

LOGGER = logging.getLogger(__name__)
HELP_TEXT = (
    "🎵 <b>Bar Lar Lar • DJ Music Downloader</b>\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "🔎 <b>Search Methods</b>\n"
    "• <code>/search artist title</code> - Standard YouTube/SoundCloud search\n"
    "• <code>/aisearch energetic house 120-130 bpm</code> - AI-powered DJ search\n"
    "  Understands: genre, BPM, mood, language, region, version\n"
    "• <code>/title song name</code> - Search by title only\n"
    "• <code>/artist artist name</code> - Search by artist only\n"
    "• Or just send keywords directly!\n\n"
    "🤖 <b>AI Search Examples</b>\n"
    "• <code>energetic house 128 bpm</code>\n"
    "• <code>chill ambient under 5 minutes</code>\n"
    "• <code>Myanmar hip hop 90-110 bpm</code>\n"
    "• <code>ဆိုင်းဆိုင်းမော် အချစ်သီချင်း</code>\n"
    "• <code>华语 DJ舞曲 串烧</code>\n\n"
    "📜 <b>History &amp; Favorites</b>\n"
    "• <code>/history</code> - View recent searches (re-run or save)\n"
    "• <code>/favorites</code> - Quick access to saved searches\n\n"
    "🎛️ <b>Smart Filters</b>\n"
    "After search results appear:\n"
    "• 🥁 <b>BPM</b> - Filter by tempo ranges (60-90, 120-130, 140-180...)\n"
    "• 🔥 <b>Energy</b> - High/Medium/Low energy tracks\n"
    "• ⏱️ <b>Duration</b> - Filter by length (<3min, 3-5min, 8+min...)\n"
    "• ⚙️ <b>All Filters</b> - Source, genre, version, quality\n\n"
    "⚙️ <b>Settings</b>\n"
    "• <code>/settings</code> - Configure bitrate (128-320 kbps) &amp; default source\n"
    "• <code>/language</code> - Switch language (English/Burmese/Chinese)\n"
    "• <code>/menu</code> - Show keyboard shortcuts\n\n"
    "📊 <b>What You Get</b>\n"
    "Every download includes:\n"
    "• High-quality MP3 audio (configurable bitrate)\n"
    "• DJ metadata (BPM, musical key, Camelot notation)\n"
    "• Quality score &amp; audio analysis\n"
    "• JSON &amp; CSV exports for DJ software\n"
    "• Match score showing search relevance\n\n"
    "💡 <b>Pro Tips</b>\n"
    "• AI search works in any language (Burmese/Chinese/English)\n"
    "• Use BPM ranges for accurate DJ mixing results\n"
    "• Save frequent searches to /favorites for quick access\n"
    "• Filter results by energy level for perfect set transitions\n\n"
    "⚖️ <i>Download only audio you have permission to use.</i>"
)
HELP_TEXTS = {
    "en": HELP_TEXT,
    "my": (
        "🎵 <b>Bar Lar Lar • DJ ဂီတဒေါင်းလုပ်</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🔎 <b>ရှာဖွေနည်းများ</b>\n"
        "• <code>/search အဆိုတော် သီချင်း</code> - သာမန် YouTube/SoundCloud\n"
        "• <code>/aisearch အားကောင်းသော house 120-130 bpm</code> - AI ဖြင့် DJ ရှာဖွေမှု\n"
        "  နားလည်သည်: genre၊ BPM၊ mood၊ ဘာသာစကား၊ ဒေသ၊ version\n"
        "• <code>/title သီချင်းအမည်</code> - သီချင်းအမည်ဖြင့်\n"
        "• <code>/artist အဆိုတော်</code> - အဆိုတော်ဖြင့်\n"
        "• သို့မဟုတ် စာသားတိုက်ရိုက်ပို့ပါ!\n\n"
        "🤖 <b>AI ရှာဖွေမှု ဥပမာများ</b>\n"
        "• <code>ဆိုင်းဆိုင်းမော် အချစ်သီချင်း</code>\n"
        "• <code>လေးဖြူ ရော့ခ်</code>\n"
        "• <code>Myanmar hip hop 90-110 bpm</code>\n"
        "• <code>အားကောင်းသော house 128 bpm</code>\n"
        "• <code>တည်ငြိမ်သော ambient 5 မိနစ်အောက်</code>\n\n"
        "📜 <b>မှတ်တမ်းနှင့် အကြိုက်ဆုံးများ</b>\n"
        "• <code>/history</code> - မကြာသေးသော ရှာဖွေမှုများ (ပြန်လုပ် သို့မဟုတ် သိမ်းဆည်း)\n"
        "• <code>/favorites</code> - သိမ်းဆည်းထားသော ရှာဖွေမှုများ\n\n"
        "🎛️ <b>စမတ် Filters</b>\n"
        "ရလဒ်များပေါ်လာပြီးနောက်:\n"
        "• 🥁 <b>BPM</b> - tempo အပိုင်းအခြားဖြင့် (60-90, 120-130, 140-180...)\n"
        "• 🔥 <b>Energy</b> - High/Medium/Low အင်အား tracks\n"
        "• ⏱️ <b>ကြာချိန်</b> - အရှည်ဖြင့် (<3min, 3-5min, 8+min...)\n"
        "• ⚙️ <b>Filters အားလုံး</b> - Source၊ genre၊ version၊ quality\n\n"
        "⚙️ <b>ဆက်တင်များ</b>\n"
        "• <code>/settings</code> - Bitrate (128-320 kbps) နှင့် default source\n"
        "• <code>/language</code> - ဘာသာစကားပြောင်း (English/Burmese/Chinese)\n"
        "• <code>/menu</code> - Keyboard shortcuts ပြရန်\n\n"
        "📊 <b>ရရှိမည့်အရာများ</b>\n"
        "ဒေါင်းလုပ်တိုင်းတွင် ပါဝင်သည်:\n"
        "• အရည်အသွေးမြင့် MP3 (bitrate ချိန်ညှိနိုင်)\n"
        "• DJ metadata (BPM၊ musical key၊ Camelot)\n"
        "• Quality score နှင့် audio analysis\n"
        "• DJ software အတွက် JSON &amp; CSV\n"
        "• ရှာဖွေမှု ကိုက်ညီမှု score\n\n"
        "💡 <b>အကြံပြုချက်များ</b>\n"
        "• AI search သည် မည်သည့်ဘာသာစကားဖြင့်မဆို အလုပ်လုပ်သည်\n"
        "• DJ mixing အတွက် BPM ranges အသုံးပြုပါ\n"
        "• မကြာခဏရှာသော အရာများကို /favorites တွင် သိမ်းဆည်းပါ\n"
        "• Set transitions အတွက် energy level ဖြင့် filter လုပ်ပါ\n\n"
        "⚖️ <i>ခွင့်ပြုချက်ရှိသော အသံဖိုင်များကိုသာ ဒေါင်းလုပ်လုပ်ပါ။</i>"
    ),
    "zh": (
        "🎵 <b>Bar Lar Lar • DJ 音乐下载器</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🔎 <b>搜索方式</b>\n"
        "• <code>/search 艺术家 歌曲</code> - 标准 YouTube/SoundCloud 搜索\n"
        "• <code>/aisearch 高能量 house 120-130 bpm</code> - AI 智能 DJ 搜索\n"
        "  理解: 风格、BPM、情绪、语言、地区、版本\n"
        "• <code>/title 歌曲名</code> - 按歌曲名搜索\n"
        "• <code>/artist 艺术家</code> - 按艺术家搜索\n"
        "• 或直接发送关键词!\n\n"
        "🤖 <b>AI 搜索示例</b>\n"
        "• <code>华语 DJ舞曲 串烧</code>\n"
        "• <code>粤语 流行 抒情</code>\n"
        "• <code>高能量 house 128 bpm</code>\n"
        "• <code>放松 ambient 5分钟以下</code>\n"
        "• <code>中文说唱 90-110 bpm</code>\n\n"
        "📜 <b>历史记录与收藏</b>\n"
        "• <code>/history</code> - 查看最近搜索 (重新运行或保存)\n"
        "• <code>/favorites</code> - 快速访问已保存的搜索\n\n"
        "🎛️ <b>智能过滤器</b>\n"
        "搜索结果出现后:\n"
        "• 🥁 <b>BPM</b> - 按节奏范围过滤 (60-90, 120-130, 140-180...)\n"
        "• 🔥 <b>能量</b> - 高/中/低能量曲目\n"
        "• ⏱️ <b>时长</b> - 按长度过滤 (<3分钟, 3-5分钟, 8+分钟...)\n"
        "• ⚙️ <b>全部过滤器</b> - 来源、风格、版本、音质\n\n"
        "⚙️ <b>设置</b>\n"
        "• <code>/settings</code> - 配置比特率 (128-320 kbps) 和默认来源\n"
        "• <code>/language</code> - 切换语言 (English/Burmese/Chinese)\n"
        "• <code>/menu</code> - 显示快捷键盘\n\n"
        "📊 <b>下载内容</b>\n"
        "每次下载包含:\n"
        "• 高品质 MP3 音频 (可配置比特率)\n"
        "• DJ 元数据 (BPM、音乐调式、Camelot 标记)\n"
        "• 质量评分和音频分析\n"
        "• DJ 软件用 JSON 和 CSV 导出\n"
        "• 搜索相关性匹配分数\n\n"
        "💡 <b>专业提示</b>\n"
        "• AI 搜索支持任何语言 (中文/缅甸语/英语)\n"
        "• 使用 BPM 范围获得精准的 DJ 混音结果\n"
        "• 将常用搜索保存到 /favorites 快速访问\n"
        "• 按能量级别过滤以实现完美的混音过渡\n\n"
        "⚖️ <i>请只下载您有权使用的音频。</i>"
    ),
}
SEARCH_PAGE_SIZE = 5
LANGUAGES = {
    "en": {"name": "English", "search": "Search", "ai_search": "AI Search", "help": "Help", "language": "Language"},
    "my": {"name": "မြန်မာ", "search": "ရှာဖွေရန်", "ai_search": "AI ရှာဖွေရန်", "help": "အကူအညီ", "language": "ဘာသာစကား"},
    "zh": {"name": "中文", "search": "搜索音乐", "ai_search": "AI 搜索", "help": "帮助", "language": "语言"},
}
BOT_COMMANDS = [
    BotCommand("start", "Start Bar Lar Lar"),
    BotCommand("help", "Show help and usage"),
    BotCommand("search", "Search by artist and title"),
    BotCommand("aisearch", "AI-assisted DJ source search"),
    BotCommand("title", "Search by song title"),
    BotCommand("artist", "Search by artist name"),
    BotCommand("history", "View recent searches"),
    BotCommand("favorites", "View favorite searches"),
    BotCommand("language", "Choose interface language"),
    BotCommand("menu", "Show the music keyboard"),
]


def create_application(config: Config) -> Application:
    async def configure_command_menu(application: Application) -> None:
        try:
            await application.bot.set_my_commands(BOT_COMMANDS)
            LOGGER.info("Telegram command menu configured")
        except RetryAfter as exc:
            LOGGER.warning("Telegram command menu rate-limited for %s seconds; keeping existing menu", exc.retry_after)
        except TelegramError:
            LOGGER.exception("Could not update Telegram command menu; continuing startup")

    application = (
        Application.builder()
        .token(config.bot_token)
        .request(HTTPXRequest(connect_timeout=30, read_timeout=60, write_timeout=60, pool_timeout=30))
        .get_updates_request(HTTPXRequest(connect_timeout=30, read_timeout=90, write_timeout=60, pool_timeout=30))
        .post_init(configure_command_menu)
        .build()
    )
    semaphore = asyncio.Semaphore(config.download_workers)
    preferences = Preferences(Path("runtime/preferences.db"))
    search_history = SearchHistory(Path("runtime/search_history.db"))

    def get_ai_parser(context: ContextTypes.DEFAULT_TYPE) -> AIParser:
        """Create AIParser with user's language context."""
        language = context.user_data.get("language", "en")
        return AIParser(user_language=language)

    async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            LOGGER.info(f"Help command received from user {update.effective_user.id if update.effective_user else 'unknown'}")
            if update.message:
                await update.message.reply_text(HELP_TEXTS[_language(context)], parse_mode="HTML", disable_web_page_preview=True, reply_markup=_menu(context))
                LOGGER.info("Help message sent successfully")
        except Exception as e:
            LOGGER.error(f"Error in help_handler: {e}", exc_info=True)
            if update.message:
                await update.message.reply_text("Sorry, an error occurred. Please try again.")

    async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            await update.message.reply_text(f"{emoji('settings')} Music controls are ready below.", parse_mode="HTML", reply_markup=_menu(context))

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
                f"{emoji('settings')} Choose your language / ဘာသာစကား / 语言:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("English", callback_data="lang:en")],
                    [InlineKeyboardButton("ဗမာ (Burmese)", callback_data="lang:my")],
                    [InlineKeyboardButton("中文 (Chinese)", callback_data="lang:zh")],
                ]),
            )

    async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show recent search history with re-run option."""
        if not update.message or not update.effective_user:
            return
        recent = search_history.get_recent(update.effective_user.id, limit=10)
        if not recent:
            await update.message.reply_text(
                "📜 No search history yet.\nStart searching with /search or /aisearch!",
                parse_mode="HTML",
            )
            return
        
        text = "📜 <b>Recent Searches</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for i, entry in enumerate(recent, 1):
            fav_icon = "⭐" if entry.is_favorite else ""
            text += f"{i}. {fav_icon}<code>{escape(entry.query[:50])}</code>\n"
            text += f"   📊 {entry.result_count} results\n\n"
            buttons.append([
                InlineKeyboardButton(f"🔁 Re-run #{i}", callback_data=f"history_rerun:{entry.query}"),
                InlineKeyboardButton(f"{'⭐ Unfav' if entry.is_favorite else '⭐ Favorite'}", callback_data=f"history_fav:{entry.query}"),
            ])
        
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons[:10]),
        )

    async def favorites_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show favorite searches."""
        if not update.message or not update.effective_user:
            return
        favorites = search_history.get_favorites(update.effective_user.id)
        if not favorites:
            await update.message.reply_text(
                "⭐ No favorites yet.\nMark searches as favorites from /history!",
                parse_mode="HTML",
            )
            return
        
        text = "⭐ <b>Favorite Searches</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for i, entry in enumerate(favorites, 1):
            text += f"{i}. <code>{escape(entry.query[:50])}</code>\n"
            text += f"   📊 {entry.result_count} results\n\n"
            buttons.append([InlineKeyboardButton(f"🔁 Re-run #{i}", callback_data=f"history_rerun:{entry.query}")])
        
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    async def history_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle history re-run and favorite toggle."""
        query = update.callback_query
        if not query or not query.data or not update.effective_user:
            return
        
        await query.answer()
        action, search_query = query.data.split(":", 1)
        
        if action == "history_rerun":
            # Re-run the search
            context.user_data["pending_search_query"] = search_query
            await query.message.edit_text(
                f"🔁 Re-running search: <code>{escape(search_query)}</code>",
                parse_mode="HTML",
            )
            # Trigger search
            await run_search(update, context, search_query, use_ai=True)
        
        elif action == "history_fav":
            # Toggle favorite
            new_status = search_history.toggle_favorite(update.effective_user.id, search_query)
            await query.answer(f"{'⭐ Added to' if new_status else '❌ Removed from'} favorites")
            # Refresh history view
            await history_handler(update, context)
        if update.message:
            await update.message.reply_text(HELP_TEXTS[_language(context)], parse_mode="HTML", disable_web_page_preview=True, reply_markup=_menu(context))

    async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            await update.message.reply_text(f"{emoji('settings')} Music controls are ready below.", parse_mode="HTML", reply_markup=_menu(context))

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
                f"{emoji('settings')} Choose your language / ဘာသာစကား / 语言:",
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
            f"{emoji('search')} <b>Searching</b>\n<code>{escape(query.strip())}</code>\n\n⏳ Finding the best matches...",
            parse_mode="HTML",
        )
        try:
            parsed = await get_ai_parser(context).parse_async(query) if use_ai else None
            intent = parsed.intent if parsed else None
            if use_ai and parsed:
                if parsed.used_ai:
                    context.user_data["pending_ai_query"] = query
                    context.user_data["pending_ai_intent"] = parsed.intent
                    context.user_data["pending_ai_owner"] = update.effective_user.id if update.effective_user else None
                    await status.edit_text(
                        _intent_preview(parsed.intent, parsed.confidence),
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("✅ Search exactly", callback_data="ai_confirm")],
                            [InlineKeyboardButton("✏️ Edit request", callback_data="ai_edit")],
                        ]),
                    )
                    return
                else:
                    reason = "timed out" if parsed.fallback_reason == "timeout" else "is unavailable"
                    await status.edit_text(f"{emoji('warning')} AI {reason}. Using local DJ parsing instead...", parse_mode="HTML")
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
                intent=intent,
            )
            if not results:
                raise DownloadError("No results under 15 minutes were found. Try another keyword.")
            # Record search in history
            if update.effective_user:
                search_history.add(update.effective_user.id, query, intent, len(results))
            context.user_data["search_results"] = results
            context.user_data["search_query"] = query
            context.user_data["search_field"] = field
            context.user_data["search_use_ai"] = use_ai
            context.user_data["search_source"] = "youtube"
            if update.effective_user:
                context.user_data["search_source"] = preferences.get(update.effective_user.id)["source"]
            context.user_data["search_genre"] = None
            context.user_data["advanced_filters"] = {}
            context.user_data["search_owner"] = update.effective_user.id if update.effective_user else None
            first = results[0] if results else None
            if first and first.thumbnail:
                await status.delete()
                preview = await message.reply_photo(first.thumbnail)
                await _show_search_page(preview, context, 0)
            else:
                await _show_search_page(status, context, 0)
        except DownloadError as exc:
            await status.edit_text(f"{emoji('warning')} {escape(str(exc))}", parse_mode="HTML")
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
        advanced = context.user_data.get("advanced_filters", {})
        status = await message.reply_text(f"{emoji('search')} Searching {selected_source} for {escape(query)}...", parse_mode="HTML")
        try:
            search_query = query
            intent = None
            if context.user_data.get("search_use_ai"):
                parsed = await get_ai_parser(context).parse_async(query)
                intent = parsed.intent if parsed.used_ai else None
                search_query = provider_query(intent) if intent else query
            results = await asyncio.to_thread(
                search_tracks,
                search_query,
                field="search",
                max_duration=min(config.max_duration_seconds, 900),
                cookies_file=config.cookies_file,
                source=selected_source,
                intent=intent,
            )
            results = apply_advanced_filters(results, advanced)
            if not results:
                raise DownloadError("No tracks match those filters. Try a broader filter.")
            context.user_data["search_results"] = results
            context.user_data["search_source"] = selected_source
            context.user_data["search_query"] = query
            if genre is not None:
                context.user_data["search_genre"] = genre
            await _show_search_page(status, context, 0)
        except DownloadError as exc:
            await status.edit_text(f"{emoji('warning')} {escape(str(exc))}", parse_mode="HTML")

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

    async def ai_confirmation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or query.from_user.id != context.user_data.get("pending_ai_owner"):
            return
        action = query.data
        if action == "ai_edit":
            await query.answer()
            await query.edit_message_text("✏️ Send your corrected DJ search request.")
            context.user_data["ai_search_mode"] = True
            return
        intent = context.user_data.pop("pending_ai_intent", None)
        original = context.user_data.pop("pending_ai_query", None)
        if not intent or not original:
            await query.answer("This interpretation expired. Search again.", show_alert=True)
            return
        await query.answer()
        await query.edit_message_text("🔎 Searching the confirmed interpretation...")
        try:
            results = await search_multiple_sources(
                provider_query(intent),
                max_duration=min(config.max_duration_seconds, 900),
                cookies_file=config.cookies_file,
            )
            context.user_data["search_results"] = results
            context.user_data["search_query"] = original
            context.user_data["search_use_ai"] = True
            context.user_data["search_source"] = preferences.get(query.from_user.id)["source"]
            context.user_data["search_owner"] = query.from_user.id
            context.user_data["advanced_filters"] = {}
            await _show_search_page(query.message, context, 0)
        except DownloadError as exc:
            await query.edit_message_text(f"⚠️ {escape(str(exc))}")

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
        context.user_data["fallback_query"] = f"{result.artist} {result.title}"
        await download_url(update, context, result.url, reply_to=query.message.message_id)

    async def fallback_source_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query:
            return
        if query.from_user.id != context.user_data.get("search_owner"):
            await query.answer("Run your own search to use a fallback source.", show_alert=True)
            return
        fallback_query = context.user_data.get("fallback_query")
        if not fallback_query:
            await query.answer("The fallback search has expired.", show_alert=True)
            return
        context.user_data["search_query"] = fallback_query
        await query.answer()
        await run_filtered_search(update, context, source="soundcloud")

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
        await query.edit_message_text(f"{emoji('success')} Language: {LANGUAGES[language]['name']}", parse_mode="HTML")
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
            [InlineKeyboardButton("🥁 BPM range", callback_data="advanced:bpm")],
            [InlineKeyboardButton("⏱️ Duration", callback_data="advanced:duration")],
            [InlineKeyboardButton("🎛️ Version", callback_data="advanced:version")],
            [InlineKeyboardButton("💿 Quality", callback_data="advanced:quality")],
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

    async def quickfilter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle quick DJ filter buttons (BPM, Energy, Duration)."""
        query = update.callback_query
        if not query or query.from_user.id != context.user_data.get("search_owner"):
            return
        
        filter_type = (query.data or "").split(":", 1)[1]
        await query.answer()
        
        if filter_type == "bpm":
            keyboard = [
                [InlineKeyboardButton("🥁 60-90 BPM (Hip-Hop/Chill)", callback_data="bpmfilter:60-90")],
                [InlineKeyboardButton("🥁 90-110 BPM (Trap/Moombah)", callback_data="bpmfilter:90-110")],
                [InlineKeyboardButton("🥁 120-130 BPM (House)", callback_data="bpmfilter:120-130")],
                [InlineKeyboardButton("🥁 130-140 BPM (Techno)", callback_data="bpmfilter:130-140")],
                [InlineKeyboardButton("🥁 140-180 BPM (D&B/Hardstyle)", callback_data="bpmfilter:140-180")],
                [InlineKeyboardButton("↩️ Back", callback_data="filter:back")],
            ]
        elif filter_type == "energy":
            keyboard = [
                [InlineKeyboardButton("🔥 High Energy (Fast/Aggressive)", callback_data="energyfilter:high")],
                [InlineKeyboardButton("⚡ Medium Energy (Groovy)", callback_data="energyfilter:medium")],
                [InlineKeyboardButton("🌙 Low Energy (Chill/Ambient)", callback_data="energyfilter:low")],
                [InlineKeyboardButton("↩️ Back", callback_data="filter:back")],
            ]
        elif filter_type == "duration":
            keyboard = [
                [InlineKeyboardButton("⏱️ Under 3 min (Radio Edit)", callback_data="durationfilter:0-180")],
                [InlineKeyboardButton("⏱️ 3-5 min (Standard)", callback_data="durationfilter:180-300")],
                [InlineKeyboardButton("⏱️ 5-8 min (Extended)", callback_data="durationfilter:300-480")],
                [InlineKeyboardButton("⏱️ 8+ min (Long Mix)", callback_data="durationfilter:480-900")],
                [InlineKeyboardButton("↩️ Back", callback_data="filter:back")],
            ]
        else:
            return
        
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

    async def apply_quick_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Apply BPM/energy/duration quick filters and refresh results."""
        query = update.callback_query
        if not query or query.from_user.id != context.user_data.get("search_owner"):
            return
        
        filter_data = query.data or ""
        if filter_data.startswith("bpmfilter:"):
            bpm_range = filter_data.split(":", 1)[1]
            context.user_data.setdefault("advanced_filters", {})["bpm_range"] = bpm_range
            await query.answer(f"🥁 BPM {bpm_range} filter applied")
        elif filter_data.startswith("energyfilter:"):
            energy = filter_data.split(":", 1)[1]
            context.user_data.setdefault("advanced_filters", {})["energy"] = energy
            await query.answer(f"🔥 {energy.title()} energy filter applied")
        elif filter_data.startswith("durationfilter:"):
            duration = filter_data.split(":", 1)[1]
            min_dur, max_dur = map(int, duration.split("-"))
            # Filter results by duration
            results = context.user_data.get("search_results", [])
            filtered = [r for r in results if min_dur <= r.duration <= max_dur]
            context.user_data["search_results"] = filtered
            await query.answer(f"⏱️ Duration {min_dur//60}-{max_dur//60}min filter applied")
        
        # Refresh search page
        await _show_search_page(query.message, context, 0)

    async def advanced_filter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or query.from_user.id != context.user_data.get("search_owner"):
            return
        kind = (query.data or "").split(":", 1)[1]
        options = {
            "bpm": [("120-124 BPM", "120-124 bpm"), ("125-128 BPM", "125-128 bpm"), ("129-135 BPM", "129-135 bpm")],
            "duration": [("Under 5 minutes", "under 5 minutes"), ("5-10 minutes", "5 to 10 minutes"), ("10-15 minutes", "10 to 15 minutes")],
            "version": [("Remix", "Remix"), ("Extended mix", "Extended Mix"), ("Instrumental", "Instrumental"), ("Acapella", "Acapella")],
            "quality": [("320 kbps source", "320 kbps"), ("Lossless / FLAC", "lossless FLAC")],
        }
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(label, callback_data=f"advanced_set:{kind}:{value}")]
            for label, value in options[kind]
        ] + [[InlineKeyboardButton("↩️ Back", callback_data="filter:panel")]]))

    async def advanced_set_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or query.from_user.id != context.user_data.get("search_owner"):
            return
        _, kind, value = (query.data or "").split(":", 2)
        context.user_data.setdefault("advanced_filters", {})[kind] = value
        await query.answer(f"{kind.title()} filter applied")
        await run_filtered_search(update, context)

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Network errors during long-polling are expected; suppress noise
        if isinstance(context.error, NetworkError):
            LOGGER.debug("Telegram network error (auto-retry): %s", context.error)
            return
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
        provider = detect_provider(url)
        if provider and provider.metadata_only and provider.key not in {"spotify"}:
            await message.reply_text(
                f"ℹ️ {provider.label} provides metadata only. Send a public audio link from a permitted source."
            )
            return
        if provider and not provider.direct_download and provider.key not in {"spotify"}:
            await message.reply_text(f"⚠️ Direct downloads are not enabled for {provider.label}.")
            return
        status = await message.reply_text(
            f"{emoji('download')} <b>Processing your link</b>\n⏳ Extracting audio...", parse_mode="HTML"
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
                    await status.edit_text(f"{emoji('success')} <b>Track ready</b>\n⬆️ Uploading MP3...", parse_mode="HTML")
                    await message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
                    TELEGRAM_LIMIT_MB = 50
                    caption = _analysis_caption(track.artist, track.title, analysis)
                    upload_path = track.path
                    file_size_mb = upload_path.stat().st_size / (1024 * 1024)

                    if file_size_mb > TELEGRAM_LIMIT_MB:
                        await status.edit_text(
                            f"📦 <b>Compressing for Telegram</b>\n"
                            f"{file_size_mb:.0f} MB → target {TELEGRAM_LIMIT_MB} MB...",
                            parse_mode="HTML",
                        )
                        upload_path = await asyncio.to_thread(
                            _compress_mp3, upload_path, Path(temp_dir), TELEGRAM_LIMIT_MB
                        )
                        if upload_path is None:
                            await status.edit_text(
                                "❌ File is too large to upload via Telegram even after compression."
                            )
                            return

                    with upload_path.open("rb") as audio_file:
                        await message.reply_audio(
                            audio=audio_file, title=track.title, performer=track.artist,
                            duration=track.duration or None,
                            caption=caption,
                        )
                    with json_path.open("rb") as json_file:
                        await message.reply_document(json_file, caption="📋 DJ metadata (JSON)")
                    with csv_path.open("rb") as csv_file:
                        await message.reply_document(csv_file, caption="📊 DJ metadata (CSV)")
            await status.delete()
        except DownloadError as exc:
            provider = detect_provider(url)
            markup = None
            if provider and provider.key == "youtube" and context.user_data.get("fallback_query"):
                markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton("☁️ Try SoundCloud", callback_data="fallback:soundcloud")
                ]])
            await status.edit_text(
                f"⚠️ {escape(str(exc))}", parse_mode="HTML", reply_markup=markup
            )
        except Exception:
            LOGGER.exception("Unexpected failure while downloading %s", url)
            await status.edit_text("❌ An unexpected error occurred while downloading.")

    application.add_handler(CommandHandler(["start", "help"], help_handler))
    application.add_handler(CommandHandler("history", history_handler))
    application.add_handler(CommandHandler("favorites", favorites_handler))
    application.add_handler(CommandHandler("language", language_handler))
    application.add_handler(CommandHandler("menu", menu_handler))
    application.add_handler(CommandHandler("settings", settings_handler))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("aisearch", ai_search_command))
    application.add_handler(CallbackQueryHandler(ai_confirmation_handler, pattern=r"^ai_(confirm|edit)$"))
    application.add_handler(CallbackQueryHandler(history_callback_handler, pattern=r"^history_(rerun|fav):.+$"))
    application.add_handler(CallbackQueryHandler(quickfilter_handler, pattern=r"^quickfilter:(bpm|energy|duration)$"))
    application.add_handler(CallbackQueryHandler(apply_quick_filter, pattern=r"^(bpmfilter|energyfilter|durationfilter):.+$"))
    application.add_handler(CommandHandler(["title", "artist"], field_command))
    application.add_handler(CallbackQueryHandler(pick_handler, pattern=r"^pick:\d+$"))
    application.add_handler(CallbackQueryHandler(next_handler, pattern=r"^next:\d+$"))
    application.add_handler(CallbackQueryHandler(language_callback, pattern=r"^lang:(en|my|zh)$"))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^settings:(bitrate|source|back)$"))
    application.add_handler(CallbackQueryHandler(setting_callback, pattern=r"^set:(bitrate|source):.+$"))
    application.add_handler(CallbackQueryHandler(fallback_source_handler, pattern=r"^fallback:soundcloud$"))
    application.add_handler(CallbackQueryHandler(filter_panel_handler, pattern=r"^filters$"))
    application.add_handler(CallbackQueryHandler(filter_choice_handler, pattern=r"^filter:(source|genre|urls|metadata|panel|back)$"))
    application.add_handler(CallbackQueryHandler(source_handler, pattern=r"^source:(youtube|soundcloud)$"))
    application.add_handler(CallbackQueryHandler(genre_handler, pattern=r"^genre:(D&B|House|Vinahouse|Bounce|Dubstep|SpeedHouse|Custom)$"))
    application.add_handler(CallbackQueryHandler(advanced_filter_handler, pattern=r"^advanced:(bpm|duration|version|quality)$"))
    application.add_handler(CallbackQueryHandler(advanced_set_handler, pattern=r"^advanced_set:(bpm|duration|version|quality):.+$"))
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
    
    # Quick DJ filters row
    dj_filters = [
        InlineKeyboardButton("🥁 BPM", callback_data="quickfilter:bpm"),
        InlineKeyboardButton("🔥 Energy", callback_data="quickfilter:energy"),
        InlineKeyboardButton("⏱️ Duration", callback_data="quickfilter:duration"),
    ]
    keyboard.append(dj_filters)
    keyboard.append([InlineKeyboardButton("⚙️ All Filters", callback_data="filters")])
    
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
    label = f"🎵 {index + 1}. {result.artist} - {result.title} · {result.version} · {result.source} · {result.match_score}%"
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


def _intent_preview(intent, confidence: int | None = None) -> str:
    def value(item) -> str:
        return escape(str(item)) if item not in (None, "") else "not specified"

    bpm = "not specified"
    if intent.min_bpm is not None:
        bpm = f"{intent.min_bpm:.0f}"
        if intent.max_bpm is not None and intent.max_bpm != intent.min_bpm:
            bpm += f"-{intent.max_bpm:.0f}"
    confidence_line = f"🎯 Interpretation confidence: {confidence}%\n" if confidence is not None else ""
    guidance = (
        "⚠️ Review carefully: this request is broad. Add an artist, title, genre, or region.\n\n"
        if confidence is not None and confidence < 60 else ""
    )
    return (
        f"🤖 <b>AI interpretation</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 Artist: {value(intent.artist)}\n"
        f"🎵 Title: {value(intent.title)}\n"
        f"🔎 Search mode: {value(intent.search_mode)}\n"
        f"🎚️ Genre: {value(intent.genre)}\n"
        f"🌐 Language: {value(intent.language)}\n"
        f"🌍 Region: {value(intent.region)}\n"
        f"🎛️ Version: {value(intent.version)}\n"
        f"⭐ Popularity: {value(intent.popularity)} <i>(soft preference)</i>\n"
        f"😊 Mood: {value(intent.mood)}\n"
        f"🥁 BPM: {bpm}\n"
        f"⏱️ Maximum duration: {intent.max_duration // 60} minutes\n"
        f"🎤 Instrumental: {value(intent.instrumental)}\n\n"
        f"{confidence_line}{guidance}"
        "Please confirm before searching."
    )


async def search_multiple_sources(
    query: str,
    *,
    max_duration: int,
    cookies_file: str | None = None,
    intent = None,
) -> list[SearchResult]:
    """Search independent public providers concurrently for AI mode with intent awareness."""
    searches = await asyncio.gather(
        asyncio.to_thread(search_tracks, query, max_duration=max_duration, cookies_file=cookies_file, source="youtube", intent=intent),
        asyncio.to_thread(search_tracks, query, max_duration=max_duration, cookies_file=cookies_file, source="soundcloud", intent=intent),
        return_exceptions=True,
    )
    results: list[SearchResult] = []
    for value in searches:
        if isinstance(value, list):
            results.extend(value)
    if not results:
        raise DownloadError("No public results were found from YouTube or SoundCloud.")
    from .downloader import rank_search_results
    return rank_search_results(results, query, intent)


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


def _compress_mp3(source: Path, workdir: Path, target_mb: int) -> Path | None:
    """Re-encode an MP3 at a lower bitrate so it fits within *target_mb* MB.

    Returns the path to the compressed file on success, or ``None`` when the
    source is already too long to fit even at 64 kbps.
    """
    import json

    # Probe duration with ffprobe
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", str(source),
            ],
            capture_output=True, text=True, timeout=30,
            check=True,
        )
        probe = json.loads(result.stdout)
        duration = float(probe.get("format", {}).get("duration", 0))
    except Exception:
        return None

    if duration <= 0:
        return None

    # Calculate target bitrate (leave 1 MB headroom)
    target_bytes = (target_mb - 1) * 1024 * 1024
    target_bitrate_k = int((target_bytes * 8) / duration / 1000)

    # Floor at 64 kbps; if even that won't fit, give up
    MIN_BITRATE_K = 64
    if target_bitrate_k < MIN_BITRATE_K:
        return None
    target_bitrate_k = min(target_bitrate_k, 320)

    compressed = workdir / f"{source.stem}-tg{target_bitrate_k}k.mp3"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "quiet",
                "-i", str(source),
                "-codec:a", "libmp3lame",
                "-b:a", f"{target_bitrate_k}k",
                str(compressed),
            ],
            timeout=300, check=True,
        )
    except Exception:
        return None

    if not compressed.is_file():
        return None

    # If it didn't help enough, try one more aggressive round
    size_mb = compressed.stat().st_size / (1024 * 1024)
    if size_mb > target_mb:
        # Try 64k mono as last resort
        compressed2 = workdir / f"{source.stem}-tg64k.mp3"
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "quiet",
                    "-i", str(source),
                    "-codec:a", "libmp3lame",
                    "-b:a", "64k", "-ac", "1",
                    str(compressed2),
                ],
                timeout=300, check=True,
            )
            if compressed2.is_file() and compressed2.stat().st_size / (1024 * 1024) <= target_mb:
                return compressed2
        except Exception:
            pass
        return None

    return compressed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    config = Config.from_env()
    LOGGER.info("Starting Telegram Bot API music bot")
    create_application(config).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
