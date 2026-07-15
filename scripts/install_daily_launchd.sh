#!/usr/bin/env bash
# Install a daily morning job digest (macOS launchd).
# Emails once per day with openings matching your filters (US, 1–5 yrs, keywords).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/.venv/bin/python}"
PLIST_NAME="com.jobopeningmonitor.daily"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

# Default: 9:00 AM local time
HOUR="${1:-9}"
MINUTE="${2:-0}"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_BIN}</string>
        <string>${PROJECT_DIR}/run.py</string>
        <string>--digest</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${HOUR}</integer>
        <key>Minute</key>
        <integer>${MINUTE}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/data/daily_digest.log</string>
    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/data/daily_digest.error.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "Installed daily digest: $PLIST_PATH"
echo "Runs every day at ${HOUR}:$(printf '%02d' "$MINUTE") local time."
echo "Uses: python run.py --digest  (265 companies, 1–5 yrs filter, email)"
echo "Logs: ${PROJECT_DIR}/data/daily_digest.log"
