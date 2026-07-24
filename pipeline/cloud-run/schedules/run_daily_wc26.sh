#!/bin/bash
# Daily incremental scrape for FIFA World Cup 2026 → BQ dataset WC_26.
# Fetches rounds containing matches from the last 2 days (INCREMENTAL=true).
# Runs until the tournament ends (final: ~2026-07-19).
#
# Tournament IDs (confirmed 2026-07-05 via seasons_lookup.py):
#   WC 2026 tournament ID: 16
#   WC 2026 season ID:     58210
#
# launchd fires this at 09:00 daily via com.realzaragoza.wc26-daily.plist
#
# Usage (manual):
#   bash run_daily_wc26.sh
#   or: GCP_PROJECT_ID=real-zaragoza-500608 TOURNAMENT_ID=<tid> SEASON_ID=<sid> \
#         BQ_DATASET=wc_2026 INCREMENTAL=true python3 scraper_sofascore.py

set -euo pipefail

LOG=/tmp/sofascore_wc26_$(date +%Y%m%d).log
PYTHON=/opt/anaconda3/bin/python3
SCRAPER=/Users/robertsoliva/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/scrapers/scraper_sofascore.py

WC_TOURNAMENT_ID=16   # confirmed 2026-07-05
WC_SEASON_ID=58210    # confirmed 2026-07-05

echo "=== WC26 daily run: $(date) ===" | tee -a "$LOG"

GCP_PROJECT_ID=real-zaragoza-500608 \
BQ_DATASET=wc_2026 \
TOURNAMENT_ID="$WC_TOURNAMENT_ID" \
SEASON_ID="$WC_SEASON_ID" \
INCREMENTAL=true \
  "$PYTHON" "$SCRAPER" 2>&1 | tee -a "$LOG"

echo "=== Done: $(date) ===" | tee -a "$LOG"
