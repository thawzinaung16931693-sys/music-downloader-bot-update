from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

from telethon import TelegramClient, events
from telethon.tl.custom import Message
from telethon.tl.types import DocumentAttributeAudio

from .config import Config
from .downloader import DownloadError, download_track, extract_url

LOGGER = logging.getLogger(__name__)
HELP_TEXT = (
    "Send me a public music link and I will return a high-quality MP3.\n\n"
    "Supported links depend on yt-dlp and commonly include SoundCloud, YouTube, "
    "Bandcamp, and many other sites. Spotify track links are matched by artist and "
    "title to another audio source; Spotify audio itself is not downloaded.\n\n"
    "Only download audio you have permission to use."
)


def create_bot(config: Config) -> TelegramClient:
    client = TelegramClient("music_bot", config.api_id, config.api_hash)
    semaphore = asyncio.Semaphore(config.download_workers)

    @client.on(events.NewMessage(pattern=r"^/(start|help)(?:@\w+)?$"))
    async def help_handler(event: events.NewMessage.Event) -> None:
        await event.respond(HELP_TEXT, link_preview=False)

    @client.on(events.NewMessage(incoming=True))
    async def download_handler(event: events.NewMessage.Event) -> None:
        message = event.message
        if not isinstance(message, Message) or not message.raw_text:
            return
        if message.raw_text.startswith("/"):
            return

        url = extract_url(message.raw_text)
        if not url:
            await event.reply("Please send a public music link. Use /help for details.")
            return

        status = await event.reply("Processing your link...")
        try:
            async with semaphore:
                with tempfile.TemporaryDirectory(prefix="music-bot-") as temp_dir:
                    track = await asyncio.to_thread(
                        download_track,
                        url,
                        Path(temp_dir),
                        quality=config.audio_quality,
                        max_duration=config.max_duration_seconds,
                        max_file_size_mb=config.max_file_size_mb,
                        cookies_file=config.cookies_file,
                    )
                    await status.edit("Uploading MP3...")
                    await client.send_file(
                        event.chat_id,
                        track.path,
                        caption=f"{track.artist} - {track.title}",
                        reply_to=message.id,
                        mime_type="audio/mpeg",
                        voice_note=False,
                        attributes=[
                            DocumentAttributeAudio(
                                duration=track.duration,
                                title=track.title,
                                performer=track.artist,
                            )
                        ],
                    )
            await status.delete()
        except DownloadError as exc:
            await status.edit(str(exc), link_preview=False)
        except Exception:
            LOGGER.exception("Unexpected failure while processing %s", url)
            await status.edit("An unexpected error occurred while processing this link.")

    return client


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = Config.from_env()
    client = create_bot(config)
    LOGGER.info("Starting Telegram music bot")
    client.start(bot_token=config.bot_token)
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
