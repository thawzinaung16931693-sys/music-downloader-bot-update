#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/telegram-music-bot}"
cd "$APP_DIR"
git pull --ff-only
.venv/bin/pip install --requirement requirements.txt
install -m 0750 -o root -g musicbot deploy/cleanup-storage.sh /opt/telegram-music-bot-storage-cleanup.sh
install -m 0644 deploy/telegram-music-bot-storage.service /etc/systemd/system/telegram-music-bot-storage.service
install -m 0644 deploy/telegram-music-bot-storage.timer /etc/systemd/system/telegram-music-bot-storage.timer
systemctl daemon-reload
systemctl enable --now telegram-music-bot-storage.timer
systemctl restart telegram-music-bot
systemctl --no-pager --full status telegram-music-bot
