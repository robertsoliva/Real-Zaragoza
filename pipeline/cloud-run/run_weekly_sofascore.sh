#!/bin/bash
# Weekly SofaScore incremental update — run via launchd every Tuesday.
# Fetches the last 14 days for each active season and writes to BigQuery via ADC.

export HOME=/Users/robertsoliva
export GCP_PROJECT_ID=real-zaragoza-500608
export INCREMENTAL=true

PYTHON=/opt/anaconda3/bin/python3
SCRAPER=/Users/robertsoliva/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/scraper_sofascore.py
LOG=/tmp/sofascore_weekly_$(date +%Y%m%d).log

exec > "$LOG" 2>&1

echo "=== SofaScore weekly update started at $(date) ==="

echo ""
echo "[LaLiga2 2025-26] TOURNAMENT_ID=54 SEASON_ID=77558"
TOURNAMENT_ID=54 SEASON_ID=77558 "$PYTHON" "$SCRAPER"

echo ""
echo "[1RFEF 2025-26] TOURNAMENT_ID=17073 SEASON_ID=77727"
TOURNAMENT_ID=17073 SEASON_ID=77727 "$PYTHON" "$SCRAPER"

echo ""
echo "=== Weekly update complete at $(date) ==="
