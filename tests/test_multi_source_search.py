import asyncio

from music_bot.bot import search_multiple_sources


def test_multi_source_search_symbol_is_async() -> None:
    assert asyncio.iscoroutinefunction(search_multiple_sources)
