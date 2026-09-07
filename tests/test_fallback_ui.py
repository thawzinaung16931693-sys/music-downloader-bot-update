from telegram import InlineKeyboardButton


def test_soundcloud_fallback_callback_is_stable() -> None:
    button = InlineKeyboardButton("Try SoundCloud", callback_data="fallback:soundcloud")
    assert button.callback_data == "fallback:soundcloud"
