#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/.venv/bin/python}"
PLIST_NAME="com.jobopeningmonitor.apply"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

# Runs every hour; Python agent only executes during 8:00 AM CST window.
INTERVAL_SECONDS="${1:-3600}"

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
        <string>${PROJECT_DIR}/run_apply.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>RunAtLoad</key>
    <false/>
    <key>StartInterval</key>
    <integer>${INTERVAL_SECONDS}</integer>
    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/data/apply_agent.log</string>
    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/data/apply_agent.error.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "Installed apply launchd agent: $PLIST_PATH"
echo "Checks hourly; runs apply logic once daily at 8:00 AM CST."
echo "Logs: ${PROJECT_DIR}/data/apply_agent.log"
