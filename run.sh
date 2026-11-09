#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PROJECT_DIR"

if [ -f "$PROJECT_DIR/runtime/settings.toml" ]; then
    SETTINGS_FILE="$PROJECT_DIR/runtime/settings.toml"
else
    SETTINGS_FILE="$PROJECT_DIR/settings.toml"
fi

# Use the existing Pi environment and leave hardware initialization to the driver.
# POSIX shell syntax also works with cron entries that invoke `sh run.sh`.
exec sudo -n env \
    LED_SETTINGS_FILE="${LED_SETTINGS_FILE:-$SETTINGS_FILE}" \
    WEB_HOST="${WEB_HOST:-0.0.0.0}" \
    "$PROJECT_DIR/venv/bin/python" -u "$PROJECT_DIR/main.py"
