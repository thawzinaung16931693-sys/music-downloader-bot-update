#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/telegram-music-bot}"
RUNTIME_DIR="$APP_DIR/runtime"
TEMP_PREFIX="/tmp/music-bot-*"
WARNING_PERCENT="${WARNING_PERCENT:-80}"
CRITICAL_PERCENT="${CRITICAL_PERCENT:-90}"
MAX_AGE_MINUTES="${MAX_AGE_MINUTES:-60}"

log() {
  logger -t telegram-music-bot-storage -- "$*"
  printf '%s\n' "$*"
}

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this script as root or with sudo." >&2
  exit 1
fi

# Only delete temporary bot directories older than the configured age.
find /tmp -maxdepth 1 -type d -name 'music-bot-*' -mmin "+$MAX_AGE_MINUTES" -print -exec rm -rf -- {} +

# Runtime is reserved for disposable bot artifacts. Never clean the app root.
if [[ -d "$RUNTIME_DIR" ]]; then
  find "$RUNTIME_DIR" -mindepth 1 -maxdepth 1 \
    ! -name 'preferences.db' ! -name 'preferences.db-wal' ! -name 'preferences.db-shm' \
    -mmin "+$MAX_AGE_MINUTES" -print -exec rm -rf -- {} +
fi

usage_percent="$(df --output=pcent "$APP_DIR" | tail -n 1 | tr -dc '0-9')"
if [[ "$usage_percent" -ge "$CRITICAL_PERCENT" ]]; then
  log "CRITICAL: filesystem containing $APP_DIR is ${usage_percent}% full"
elif [[ "$usage_percent" -ge "$WARNING_PERCENT" ]]; then
  log "WARNING: filesystem containing $APP_DIR is ${usage_percent}% full"
else
  log "Storage check OK: filesystem containing $APP_DIR is ${usage_percent}% full"
fi
