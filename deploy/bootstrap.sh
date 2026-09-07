#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/telegram-music-bot}"
APP_USER="${APP_USER:-musicbot}"
REPO_URL="${REPO_URL:-}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this script as root or with sudo." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates ffmpeg git python3 python3-venv python3-pip

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --no-create-home --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" pull --ff-only
elif [[ -n "$REPO_URL" ]]; then
  if [[ -e "$APP_DIR" ]]; then
    echo "$APP_DIR exists but is not a Git checkout; remove it or upload the project elsewhere." >&2
    exit 1
  fi
  mkdir -p "$(dirname "$APP_DIR")"
  git clone "$REPO_URL" "$APP_DIR"
elif [[ -f "$APP_DIR/requirements.txt" ]]; then
  echo "Using the already-uploaded project at $APP_DIR"
else
  echo "Set REPO_URL or upload the project to $APP_DIR first." >&2
  exit 1
fi

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/pip" install --requirement "$APP_DIR/requirements.txt"
if [[ "${INSTALL_UNIVERSAL_FALLBACK:-false}" == "true" ]]; then
  "$APP_DIR/.venv/bin/pip" install --no-deps \
    "universal-downloader @ git+https://github.com/vmexe/universal-downloader.git@main"
fi

install -d -m 0750 -o "$APP_USER" -g "$APP_USER" "$APP_DIR/runtime"
install -m 0644 "$APP_DIR/deploy/telegram-music-bot.service" \
  /etc/systemd/system/telegram-music-bot.service
install -m 0750 -o root -g "$APP_USER" "$APP_DIR/deploy/cleanup-storage.sh" \
  /opt/telegram-music-bot-storage-cleanup.sh
install -m 0644 "$APP_DIR/deploy/telegram-music-bot-storage.service" \
  /etc/systemd/system/telegram-music-bot-storage.service
install -m 0644 "$APP_DIR/deploy/telegram-music-bot-storage.timer" \
  /etc/systemd/system/telegram-music-bot-storage.timer
systemctl daemon-reload

if [[ ! -f "$APP_DIR/.env" ]]; then
  install -m 0640 -o root -g "$APP_USER" "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "Edit $APP_DIR/.env with Telegram credentials before starting the service."
fi

chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chown root:"$APP_USER" "$APP_DIR/.env"
chmod 0640 "$APP_DIR/.env"
systemctl enable telegram-music-bot
systemctl enable telegram-music-bot-storage.timer
systemctl start telegram-music-bot-storage.timer
echo "Bootstrap complete. Configure $APP_DIR/.env, then run: systemctl start telegram-music-bot"
