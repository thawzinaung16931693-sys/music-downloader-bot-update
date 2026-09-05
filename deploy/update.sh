#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/telegram-music-bot}"
cd "$APP_DIR"
git pull --ff-only
.venv/bin/pip install --requirement requirements.txt
systemctl restart telegram-music-bot
systemctl --no-pager --full status telegram-music-bot
