from music_bot.preferences import Preferences


def test_preferences_persist_and_validate(tmp_path) -> None:
    preferences = Preferences(tmp_path / "preferences.db")
    preferences.set(42, language="zh", bitrate=192, source="soundcloud")
    assert preferences.get(42) == {"language": "zh", "bitrate": 192, "source": "soundcloud"}
