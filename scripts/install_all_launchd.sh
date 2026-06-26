#!/usr/bin/env bash
# Install hourly job monitor scheduler (no auto-apply).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

"$PROJECT_DIR/scripts/install_launchd.sh" 3600

# Remove morning/apply schedulers if previously installed.
MORNING="$HOME/Library/LaunchAgents/com.jobopeningmonitor.morning.plist"
APPLY="$HOME/Library/LaunchAgents/com.jobopeningmonitor.apply.plist"
for PLIST in "$MORNING" "$APPLY"; do
    if [[ -f "$PLIST" ]]; then
        launchctl unload "$PLIST" 2>/dev/null || true
        rm -f "$PLIST"
        echo "Removed legacy scheduler: $PLIST"
    fi
done

echo ""
echo "Scheduler setup complete:"
echo "  • Every hour → job monitor (email new postings only)"
echo ""
echo "Logs: ${PROJECT_DIR}/data/monitor.log"
echo ""
echo "Auto-apply is separate. Run manually when needed:"
echo "  python run_apply.py --force"
