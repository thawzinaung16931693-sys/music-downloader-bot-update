from music_bot.preferences import Preferences


def test_preferences_persist_and_validate(tmp_path) -> None:
    preferences = Preferences(tmp_path / "preferences.db")
    preferences.set(42, language="zh", bitrate=192, source="soundcloud")
    assert preferences.get(42) == {"language": "zh", "bitrate": 192, "source": "soundcloud"}


def test_preferences_recreate_schema_if_database_is_replaced(tmp_path) -> None:
    path = tmp_path / "preferences.db"
    preferences = Preferences(path)
    path.unlink()
    assert preferences.get(42) == {"language": "en", "bitrate": 320, "source": "youtube"}
