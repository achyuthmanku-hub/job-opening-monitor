#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/.venv/bin/python}"
PLIST_NAME="com.jobopeningmonitor.agent"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

# Runs every hour — needed to catch jobs posted 1-5 hours ago.
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
        <string>${PROJECT_DIR}/run.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>StartInterval</key>
    <integer>${INTERVAL_SECONDS}</integer>
    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/data/monitor.log</string>
    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/data/monitor.error.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "Installed launchd agent: $PLIST_PATH"
echo "Runs every $((INTERVAL_SECONDS / 60)) minutes."
echo "Logs: ${PROJECT_DIR}/data/monitor.log"
