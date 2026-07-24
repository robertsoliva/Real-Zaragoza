#!/bin/bash
# Weekly SofaScore incremental update — fires every Tuesday at 07:30 via launchd.
# Fetches rounds with matches from the last 14 days for every active season.
# Run manually any time to catch up on recent matches:
#   bash run_weekly_sofascore.sh
#
# Season IDs last verified: 2026-07-24 via seasons_lookup.py

set -euo pipefail

export HOME=/Users/robertsoliva
export GCP_PROJECT_ID=real-zaragoza-500608
export INCREMENTAL=true
export BQ_DATASET=raw

PYTHON=/opt/anaconda3/bin/python3
SCRAPER=/Users/robertsoliva/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/scrapers/scraper_sofascore.py
LOG=/tmp/sofascore_weekly_$(date +%Y%m%d_%H%M).log

exec > "$LOG" 2>&1

echo "=== SofaScore weekly incremental update started: $(date) ==="
echo "    INCREMENTAL=true — fetching last 14 days per league"
echo ""

# Inter-league pause to avoid triggering Cloudflare IP ban
PAUSE=30

run_league() {
    local name=$1 tid=$2 sid=$3
    echo "--- [$name] tournament_id=$tid season_id=$sid ---"
    TOURNAMENT_ID=$tid SEASON_ID=$sid "$PYTHON" "$SCRAPER"
    echo "    done. sleeping ${PAUSE}s..."
    sleep $PAUSE
}

# ── Autumn/Winter leagues (European domestic, Aug–Jun) ──────────────────────
run_league "LaLiga2 2025-26"            54     77558
run_league "1RFEF 2025-26"              17073  77727
run_league "Serie B 2025-26"            53     79502
run_league "Ligue 2 2025-26"            182    77357
run_league "Turkish Süper Lig 2025-26"  52     77805
run_league "Austrian Bundesliga 2025-26" 45    77382
run_league "Romanian SuperLiga 2025-26" 152    77312
run_league "Mozzart Bet Superliga 25-26" 210   76909
run_league "Eerste Divisie 2025-26"     131    77156
run_league "Moldovan Super Liga 2025-26" 685   76499
run_league "Eredivisie 2025-26"         37     77012
run_league "Belgian Pro League 2025-26" 38     77040
run_league "Liga Portugal 2025-26"      238    77806
run_league "2. Bundesliga 2025-26"      35     77333

# ── Calendar-year leagues (Spring–Autumn) ───────────────────────────────────
run_league "J1 League 2026"             196    87931
run_league "Norwegian Eliteserien 2026" 20     87809
run_league "Korean K League 1 2026"     410    88606
run_league "Brasileirao Serie B 2026"   390    89840
run_league "MLS 2026"                   242    86668
run_league "Allsvenskan 2026"           40     87925

echo ""
echo "=== Weekly update complete: $(date) ==="
echo "    Log: $LOG"
