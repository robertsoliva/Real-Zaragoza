#!/bin/bash
# Run the next season from sofascore_queue.txt and remove it from the queue.
# Skips comment lines and lines with SEASON_ID=TODO.
# Fired twice daily by launchd: 09:00 and 18:00.
#
# Usage:
#   bash run_next_from_queue.sh
#   nohup caffeinate -i bash run_next_from_queue.sh > /tmp/sofascore_$(date +%Y%m%d_%H%M).log 2>&1 &

set -euo pipefail

QUEUE=/Users/robertsoliva/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/schedules/sofascore_queue.txt
PYTHON=/opt/anaconda3/bin/python3
SCRAPER=/Users/robertsoliva/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/scrapers/scraper_sofascore.py

export GCP_PROJECT_ID=real-zaragoza-500608

# Find first runnable line: not a comment, not blank, not TODO
NEXT=$(grep -v '^\s*#' "$QUEUE" | grep -v '^\s*$' | grep -v 'TODO' | head -1 || true)

if [ -z "$NEXT" ]; then
    echo "Queue is empty or all remaining entries have TODO season IDs — nothing to run."
    exit 0
fi

TOURNAMENT_ID=$(echo "$NEXT" | awk '{print $1}')
SEASON_ID=$(echo "$NEXT"     | awk '{print $2}')
LABEL=$(echo "$NEXT"         | awk '{print $3}')

echo ""
echo "========================================"
echo "  $LABEL  [tournament=$TOURNAMENT_ID season=$SEASON_ID]"
echo "  Started: $(date)"
echo "========================================"

TOURNAMENT_ID="$TOURNAMENT_ID" SEASON_ID="$SEASON_ID" "$PYTHON" "$SCRAPER"

echo "  Finished: $(date)"
echo ""

# Remove completed line from queue (match on tournament + season IDs)
grep -v "^${TOURNAMENT_ID}[[:space:]]\+${SEASON_ID}[[:space:]]" "$QUEUE" > "${QUEUE}.tmp" \
    && mv "${QUEUE}.tmp" "$QUEUE"

echo "Removed from queue: $NEXT"
echo "Remaining in queue: $(grep -v '^\s*#' "$QUEUE" | grep -v '^\s*$' | grep -c '.' || true) seasons"
