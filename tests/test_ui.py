from music_bot.ui import emoji


def test_custom_emoji_entity_uses_exported_id() -> None:
    value = emoji("bot")
    assert 'emoji-id="5951817721468424817"' in value
    assert value.endswith("🤖</tg-emoji>")
