# Telegram Music Bot

A Telegram Bot API bot that accepts a public music link, extracts its best available
audio with yt-dlp, converts it to MP3 with FFmpeg, and sends it back as a Telegram
audio file. It uses `python-telegram-bot`; no Telethon user session or Telegram API
ID/hash is required.

## Provider behavior

- SoundCloud, YouTube, Bandcamp, and other yt-dlp-supported sites are downloaded
  directly when the source permits it.
- A Spotify track URL is resolved to artist/title metadata and matched to another
  audio source. The bot does not download or bypass DRM-protected Spotify audio.
- Spotify albums and playlists are intentionally rejected. One message produces
  at most one track.

Use the bot only for audio you own or are authorized to download. Provider support
can change when sites update their APIs or anti-bot systems.

## Requirements

- Python 3.11 or newer
- FFmpeg available on `PATH`
- A bot token from Telegram's `@BotFather`

## Setup

```powershell
cd telegram-music-bot
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with the bot token, then verify FFmpeg and start the bot:

```powershell
ffmpeg -version
python -m music_bot.bot
```

The default 49 MB limit leaves margin below the commonly available 50 MB bot upload
limit. If the bot account/API environment supports larger uploads, adjust
`MAX_FILE_SIZE_MB`. `AUDIO_QUALITY=320` requests 320 kbps MP3 encoding; it cannot
improve a lower-quality source.

Some providers may require cookies. Export a Netscape-format cookie file, set
`COOKIES_FILE=cookies.txt`, and keep that private file out of version control.

## Search commands

The bot can search for several results and lets you choose which one to download:

```text
/search Daft Punk One More Time
/title One More Time
/artist Daft Punk
```

The bot displays five numbered inline buttons at a time. Use `Next` and `Previous`
to browse more results, then click one to download that specific result. Plain text
without a URL is treated as a general keyword search.
The same commands are registered in Telegram's command menu, available from the
slash button in the chat.

Use `/language` or the persistent `🌐 Language` button to switch the interface
between English, Burmese, and Chinese. Search results include thumbnails when the
provider supplies them, and downloaded MP3 files include available title, artist,
album, and cover-art metadata.

Search uses YouTube's yt-dlp search backend, and search quality depends on the query
and available public results. Search and URL downloads use the same duration and
file-size limits.

## Tests

```powershell
pip install -r requirements-dev.txt
pytest
```

## Google Cloud VM deployment

The bot does not need a public HTTP port. A small Ubuntu LTS VM is sufficient for
light personal use. Create the VM with a supported Ubuntu image, then connect over
SSH from the Google Cloud Console or with `gcloud compute ssh`.

From the VM, install the project using the bootstrap script. For a Git deployment,
`REPO_URL` should point to a repository containing this project:

```bash
sudo REPO_URL=https://github.com/your-user/your-repo.git \
  bash deploy/bootstrap.sh
```

If this project is not in a Git repository, upload the folder to
`/opt/telegram-music-bot` first and run `sudo bash deploy/bootstrap.sh`; the script
will use the uploaded files. For a private repository, use a deploy key or upload
the files instead. Do not put bot tokens in Git.

Configure the credentials securely on the VM:

```bash
sudo nano /opt/telegram-music-bot/.env
sudo chown root:musicbot /opt/telegram-music-bot/.env
sudo chmod 640 /opt/telegram-music-bot/.env
sudo systemctl start telegram-music-bot
sudo systemctl status telegram-music-bot
```

View logs:

```bash
sudo journalctl -u telegram-music-bot -f
```

After code changes, update and restart it with:

```bash
sudo bash /opt/telegram-music-bot/deploy/update.sh
```

The service runs under a dedicated non-login `musicbot` user and automatically
restarts after failures. Keep SSH restricted to your admin IP where practical, and
do not expose unnecessary firewall ports.
