#!/bin/bash
# Daily incremental scrape for FIFA World Cup 2026 → BQ dataset WC_26.
# Fetches rounds containing matches from the last 2 days (INCREMENTAL=true).
# Runs until the tournament ends (final: ~2026-07-19).
#
# Tournament IDs (confirm with: python3 seasons_lookup.py <tournament_id>):
#   WC 2026 tournament ID: TODO — run seasons_lookup.py once IP is clear
#   WC 2026 season ID:     TODO — run seasons_lookup.py once IP is clear
#
# launchd fires this at 09:00 daily via com.realzaragoza.wc26-daily.plist
#
# Usage (manual):
#   bash run_daily_wc26.sh
#   or: GCP_PROJECT_ID=real-zaragoza-500608 TOURNAMENT_ID=<tid> SEASON_ID=<sid> \
#         BQ_DATASET=WC_26 INCREMENTAL=true python3 scraper_sofascore.py

set -euo pipefail

LOG=/tmp/sofascore_wc26_$(date +%Y%m%d).log
PYTHON=/opt/anaconda3/bin/python3
SCRAPER=/Users/robertsoliva/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/scraper_sofascore.py

# TODO: fill in once IP is clear and seasons_lookup.py confirms these IDs
WC_TOURNAMENT_ID=17
WC_SEASON_ID=TODO

echo "=== WC26 daily run: $(date) ===" | tee -a "$LOG"

GCP_PROJECT_ID=real-zaragoza-500608 \
BQ_DATASET=WC_26 \
TOURNAMENT_ID="$WC_TOURNAMENT_ID" \
SEASON_ID="$WC_SEASON_ID" \
INCREMENTAL=true \
  "$PYTHON" "$SCRAPER" 2>&1 | tee -a "$LOG"

echo "=== Done: $(date) ===" | tee -a "$LOG"
