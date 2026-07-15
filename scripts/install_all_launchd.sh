#!/usr/bin/env bash
# Install hourly + daily email schedulers (no auto-apply).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

"$PROJECT_DIR/scripts/install_launchd.sh" 3600
"$PROJECT_DIR/scripts/install_daily_launchd.sh" 9 0

# Remove apply scheduler if previously installed.
APPLY="$HOME/Library/LaunchAgents/com.jobopeningmonitor.apply.plist"
MORNING="$HOME/Library/LaunchAgents/com.jobopeningmonitor.morning.plist"
for PLIST in "$APPLY" "$MORNING"; do
    if [[ -f "$PLIST" ]]; then
        launchctl unload "$PLIST" 2>/dev/null || true
        rm -f "$PLIST"
        echo "Removed legacy scheduler: $PLIST"
    fi
done

echo ""
echo "Scheduler setup complete:"
echo "  • Every hour → new postings email (1–25h window)"
echo "  • Daily 9:00 AM → digest email (last ~48h, 1–5 yrs filter)"
echo ""
echo "Logs:"
echo "  ${PROJECT_DIR}/data/monitor.log"
echo "  ${PROJECT_DIR}/data/daily_digest.log"
echo ""
echo "Auto-apply is separate and disabled by default."
