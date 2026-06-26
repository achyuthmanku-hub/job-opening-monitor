#!/usr/bin/env bash
# Install daily 8:00 AM America/Chicago job monitor (email only, no auto-apply).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/.venv/bin/python}"
PLIST_NAME="com.jobopeningmonitor.morning"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${PROJECT_DIR}/scripts/run_morning.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TZ</key>
        <string>America/Chicago</string>
        <key>PYTHON_BIN</key>
        <string>${PYTHON_BIN}</string>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/data/morning.log</string>
    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/data/morning.error.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

# Remove legacy hourly-only apply agent if present.
LEGACY_APPLY="$HOME/Library/LaunchAgents/com.jobopeningmonitor.apply.plist"
if [[ -f "$LEGACY_APPLY" ]]; then
    launchctl unload "$LEGACY_APPLY" 2>/dev/null || true
    rm -f "$LEGACY_APPLY"
    echo "Removed legacy hourly apply agent."
fi

echo "Installed morning launchd agent: $PLIST_PATH"
echo "Runs daily at 8:00 AM CST: job monitor (new posting emails only)."
echo "Logs: ${PROJECT_DIR}/data/morning.log"
