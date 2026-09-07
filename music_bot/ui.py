from __future__ import annotations

from html import escape


# IDs from the user's Telegram custom emoji export. Fallback glyphs keep messages
# readable on clients that cannot render custom emoji.
CUSTOM_EMOJI = {
    "bot": ("5951817721468424817", "🤖"),
    "search": ("5969560892793163448", "🔍"),
    "download": ("5972193076385418588", "⬇️"),
    "success": ("5206607081334906820", "✅"),
    "settings": ("5971846335085678067", "⚙️"),
    "next": ("5969586907410075966", "➡️"),
    "metadata": ("5298501982556791386", "📋"),
    "artwork": ("5429229538527690282", "🖼️"),
    "music": ("5237745074539876417", "🎵"),
    "warning": ("5240241223632954241", "🚫"),
}


def emoji(name: str) -> str:
    emoji_id, fallback = CUSTOM_EMOJI[name]
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def escaped(value: object) -> str:
    return escape(str(value))
