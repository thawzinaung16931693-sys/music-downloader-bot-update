# Bar Lar Lar

A Telegram Bot API bot branded **Bar Lar Lar** that accepts a public music link, extracts its best available
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

## Phase 1 DJ backend

Phase 1 is developed on the `phase1-dj-ai` branch and is pushed to a separate
repository. It adds an optional OpenAI-compatible DJ query parser with a local
fallback, FFprobe technical audio analysis, and Mutagen metadata enrichment. The
bot reports codec, bitrate, duration, BPM, musical key, Camelot key, and
source-quality notes with each download.
Parsed artist, title, genre, mood, BPM, and instrumental filters are converted into
the provider search query while original user keywords are always preserved. For
example, `Popular Myanmar House Remix` is not changed into an English-house
recommendation.
AI configuration is optional and is documented in `.env.example`.

`/search` performs a normal YouTube keyword search. `/aisearch` performs an
AI-assisted DJ search and uses the Open Claw-style source plan for yt-dlp,
SoundCloud, and Bandcamp candidates. The optional `spotdl` and `bandcamp-dl` tools
are represented as provider adapters for future use; yt-dlp is the active downloader.
Normal searches do not call the AI backend. AI searches call the configured AI
endpoint first, then build the DJ source plan. BPM and musical-key analysis is
local audio analysis, not an AI guess. The analyzer inspects up to the first 60
seconds of a track, which gives tempo and key detection enough musical context
without making every download unnecessarily slow. Values are marked unknown when
confidence or source data is insufficient.
AI search reports whether the remote parser was used; endpoint failures explicitly
fall back to local DJ parsing. `AI_TIMEOUT_SECONDS` defaults to 45 seconds for
slower compatible endpoints. Requests use asynchronous HTTP, one retry by default,
and a five-minute in-memory cache for repeated queries.

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

Use `/search` for a normal YouTube keyword search. Use `/aisearch` for AI-assisted
DJ sourcing, for example:

```text
/aisearch energetic afro house between 120-124 bpm under 10 minutes
```

The bot searches up to 100 provider results and displays five numbered inline
buttons at a time. Use `Next` and `Previous` to browse all eligible results, then
click one to download that specific result. Plain text without a URL is treated as
a general keyword search.
The same commands are registered in Telegram's command menu, available from the
slash button in the chat.
The persistent keyboard also includes `🤖 AI Search`, separate from normal YouTube
`🔎 Search`.
AI Search first shows an interpretation preview with `✅ Search exactly` and
`✏️ Edit request`; provider search does not start until the user confirms.
Use `/help` for the short guide to all search commands, filters, navigation, settings,
and exported files.
Tap `🤖 AI Search`, then send a natural-language DJ request. Tap `🔎 Search` for a
normal YouTube keyword search.

Use `/language` or the persistent `🌐 Language` button to switch the interface
between English, Burmese, and Chinese. Search results include thumbnails when the
provider supplies them, and downloaded MP3 files include available title, artist,
album, and cover-art metadata.

Search uses YouTube's yt-dlp search backend, and search quality depends on the query
and available public results. Results longer than `MAX_DURATION_SECONDS` are hidden
from search. Search and URL downloads use the same duration and file-size limits.
The default maximum is 15 minutes. A provider may omit duration metadata; such a
result is allowed into the list and is checked again before download.
Results are ranked for exact artist/title relevance and DJ-friendly versions before
pagination, with official videos, live recordings, shorts, covers, and weak matches
ranked lower.
Duplicate uploads are removed while distinct versions such as extended mixes,
remixes, instrumentals, acapellas, and live versions remain available.
Every result page includes `⚙️ Filters`. Choose a source (`▶️ YouTube`,
`☁️ SoundCloud`, or other direct-URL sources) and a genre (`D&B`, `House`, `Vinahouse`, `Bounce`, `Dubstep`,
`SpeedHouse`, or `Custom`). A custom genre is entered as the next message and is
used to run the search again. Filters are applied before ranking and pagination.
Advanced filters are also available from `⚙️ Filters`: BPM range, duration, version
(remix, extended mix, instrumental, or acapella), and source-quality preference.
The bot performs a broad provider search first, then applies duration and version
filters locally so provider-specific keyword syntax cannot hide valid results.
Each result is classified as `Original/Unknown`, `Extended Mix`, `Club Mix`,
`Radio Edit`, `Remix`, `Bootleg`, `Mashup`, `Instrumental`, `Acapella`, `Live`,
`DJ Intro`, or `DJ Outro` when the provider metadata contains a matching label.

The recommended implementation order is YouTube, SoundCloud, Bandcamp, Audius,
HearThis.at, Jamendo, Free Music Archive, Internet Archive, ccMixter, then
metadata-only integrations for Spotify, Beatport, Apple Music, Deezer, Tidal, and
Traxsource. Only YouTube and SoundCloud currently provide keyword search in the
bot. The other direct sources accept their public URLs when yt-dlp can access them
and downloads are permitted by the owner.
The filter panel lists all of these categories so users can see what is supported:
YouTube and SoundCloud are searchable by keyword, direct-URL sources can be used by
sending their public track URL, and metadata-only services are clearly labelled and
cannot be selected as download sources.
Direct links are checked against the provider capability registry before download.
Spotify, Apple Music, Deezer, Tidal, Beatport, and Traxsource links are reported as
metadata-only instead of being sent to a downloader.
Download failures now identify the detected provider and distinguish hidden or
unavailable results from general provider errors. The bot suggests another
permitted source when appropriate.
When a selected YouTube result fails, the bot offers `☁️ Try SoundCloud`. This runs
a new source search for the selected artist/title and lets the user choose; the bot
never silently substitutes another recording.

Bandcamp direct links now use a provider adapter. Send a single public track URL
such as `https://artist.bandcamp.com/track/name`; album and artist pages are rejected
because this bot downloads one track per request. The artist or label must have
enabled the download, and the source license must permit your use.

Audius public track URLs use the same direct-link flow. Artist/profile pages are
rejected; send a single track URL and use only tracks the uploader permits you to
download.

HearThis.at track URLs are also validated as single-track direct links. Profile,
search, charts, and discovery pages are rejected; the uploader must permit the
download.

Jamendo public track URLs are validated as single-track links. Check the track's
Creative Commons or other license before downloading or using it in a DJ set.

Free Music Archive track URLs are validated as single-track links. Verify the
track's specific license before using it in a DJ set, public performance, remix, or
commercial project.

Internet Archive audio item and file URLs are validated as public audio links. Use
only public-domain or otherwise authorized recordings and verify the item's license
before downloading or performing it.

ccMixter public track pages are validated as single-track links. Confirm the
Creative Commons license and attribution requirements before downloading or using
the track.

## Universal downloader fallback

The optional MIT-licensed project
<https://github.com/vmexe/universal-downloader> can be installed as a fallback for
direct non-Spotify links. The bot tries its native downloader first, then uses the
external project's headless yt-dlp engine if native extraction fails:

```bash
pip install -r requirements-universal-fallback.txt
```

For a headless VM, prefer `requirements-universal-fallback-core.txt` and install
the external project's core package without its optional GUI dependencies. The
adapter is optional; if it is not installed, the native downloader remains active.
For the deployment scripts, set `INSTALL_UNIVERSAL_FALLBACK=true` before running
bootstrap or update; they install the external package with `--no-deps` because this
bot already provides its headless runtime dependencies.

The fallback is not used for Spotify URLs. Spotify Premium credentials do not
provide a legitimate MP3 download endpoint, so Spotify remains metadata/matching
only. The fallback must only be used for audio the user is authorized to download.

Downloads include a quality score, source codec/bitrate, warnings for low-quality
audio, and a warning when a high-bitrate MP3 may be an upscaled source.
Each completed download also sends track-named `.json` and `.csv` files with
the DJ analysis fields for library import or custom workflows. These files contain
the original/source quality fields and analysis confidence values.
BPM values are displayed and exported with exactly two decimal places. BPM and key
values below the confidence threshold, outside safe musical ranges, or otherwise
uncertain are reported as `unknown` instead of being presented as accurate facts.

The UI uses the supplied Telegram custom emoji set in message cards and status
messages, with normal emoji retained in keyboard labels because Telegram keyboards
do not support rich custom-emoji entities.

User preferences are available through `/settings` and the persistent `⚙️ Settings`
button. Language, bitrate, and preferred searchable source are stored per user in
`runtime/preferences.db` and survive service restarts.
The storage cleanup explicitly preserves this database and its SQLite journal files;
the preference store also recreates its schema safely if the database is missing.

## Tests

```powershell
pip install -r requirements-dev.txt
pytest
```

GitHub Actions runs the same compilation and pytest checks on Python 3.13 for every
push and pull request to `main`. The workflow does not use production bot, AI, or
cookie secrets.

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

### Storage cleanup

The deployment installs `telegram-music-bot-storage.timer`, which runs hourly and
removes stale `music-bot-*` temporary directories older than 60 minutes. It also
checks the filesystem containing the application and writes warnings at 80% usage
and critical alerts at 90% usage to the system journal. It does not remove `.env`,
cookies, Git data, or application files.

Inspect the timer and storage logs:

```bash
sudo systemctl status telegram-music-bot-storage.timer
sudo journalctl -t telegram-music-bot-storage -n 30 --no-pager
```

Run a cleanup manually if needed:

```bash
sudo systemctl start telegram-music-bot-storage.service
```
