#!/bin/bash
# Weekly Transfermarkt league scrape — run manually or via separate launchd job.
# Usage: bash pipeline/run_transfermarkt_leagues.sh [--league ES2] [--dry-run]
set -euo pipefail

export GCP_PROJECT_ID=real-zaragoza-500608
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

PYTHON=/opt/anaconda3/bin/python3
SCRAPER=/Users/robertsoliva/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/scrapers/scraper_transfermarkt_leagues.py
LOG=/tmp/tm_leagues_$(date +%Y%m%d_%H%M).log

echo "Starting TM league scrape at $(date)" | tee "$LOG"
$PYTHON "$SCRAPER" "$@" 2>&1 | tee -a "$LOG"
echo "Done at $(date)" | tee -a "$LOG"
