#!/bin/bash
# Weekly SofaScore incremental update — run via launchd every Tuesday.
# Fetches the last 14 days for each active season and writes to BigQuery via ADC.
#
# To find season IDs for new leagues run:
#   python seasons_lookup.py 53 182 152 196

export HOME=/Users/robertsoliva
export GCP_PROJECT_ID=real-zaragoza-500608
export INCREMENTAL=true

PYTHON=/opt/anaconda3/bin/python3
SCRAPER=/Users/robertsoliva/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/scraper_sofascore.py
LOG=/tmp/sofascore_weekly_$(date +%Y%m%d).log

exec > "$LOG" 2>&1

echo "=== SofaScore weekly update started at $(date) ==="

# --- Spanish leagues ---
echo ""
echo "[LaLiga2 2025-26] TOURNAMENT_ID=54 SEASON_ID=77558"
TOURNAMENT_ID=54 SEASON_ID=77558 "$PYTHON" "$SCRAPER"

echo ""
echo "[1RFEF 2025-26] TOURNAMENT_ID=17073 SEASON_ID=77727"
TOURNAMENT_ID=17073 SEASON_ID=77727 "$PYTHON" "$SCRAPER"

# --- Other European leagues (2025-26 season) ---
echo ""
echo "[Serie B 2025-26] TOURNAMENT_ID=53 SEASON_ID=79502"
TOURNAMENT_ID=53 SEASON_ID=79502 "$PYTHON" "$SCRAPER"

echo ""
echo "[Ligue 2 2025-26] TOURNAMENT_ID=182 SEASON_ID=77357"
TOURNAMENT_ID=182 SEASON_ID=77357 "$PYTHON" "$SCRAPER"

echo ""
echo "[Romanian SuperLiga 2025-26] TOURNAMENT_ID=152 SEASON_ID=77312"
TOURNAMENT_ID=152 SEASON_ID=77312 "$PYTHON" "$SCRAPER"

# --- Asian leagues (2026 calendar-year season) ---
echo ""
echo "[J1 League 2026] TOURNAMENT_ID=196 SEASON_ID=87931"
TOURNAMENT_ID=196 SEASON_ID=87931 "$PYTHON" "$SCRAPER"

echo ""
echo "=== Weekly update complete at $(date) ==="
