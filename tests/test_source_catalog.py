from music_bot.source_catalog import SOURCE_CATALOG, source_definition


def test_source_catalog_has_recommended_order() -> None:
    assert [source.key for source in SOURCE_CATALOG[:4]] == [
        "youtube", "soundcloud", "bandcamp", "audius"
    ]
    assert source_definition("spotify").mode == "metadata"
    assert source_definition("bandcamp").mode == "url"
