#!/bin/bash
# Full historical backfill — all leagues, 2 seasons each.
# Run once after truncating BQ tables. Takes ~8-12 hours; leave overnight.
#
# Usage:
#   bash backfill_all.sh             # run all
#   bash backfill_all.sh 2>&1 | tee /tmp/backfill_$(date +%Y%m%d).log

set -euo pipefail

export GCP_PROJECT_ID=real-zaragoza-500608
PYTHON=/opt/anaconda3/bin/python3
SCRAPER=/Users/robertsoliva/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/scraper_sofascore.py

run() {
    local label="$1" tid="$2" sid="$3"
    echo ""
    echo "========================================"
    echo "  $label  [tournament=$tid season=$sid]"
    echo "  Started: $(date)"
    echo "========================================"
    TOURNAMENT_ID="$tid" SEASON_ID="$sid" "$PYTHON" "$SCRAPER"
    echo "  Finished: $(date)"
    echo ""
    # Brief pause between runs to let connections settle
    sleep 10
}

echo "=== BACKFILL STARTED: $(date) ==="
echo "Scraping 12 season/league combinations — estimated 10-14 hours total."
echo ""

# -----------------------------------------------------------------------
# Spanish leagues (existing — re-scraped to fix null player stats)
# -----------------------------------------------------------------------
run "LaLiga2 2024-25"    54    62048
run "LaLiga2 2025-26"    54    77558
run "1RFEF 2024-25"      17073 64430
run "1RFEF 2025-26"      17073 77727

# -----------------------------------------------------------------------
# Serie B (Italy)
# -----------------------------------------------------------------------
run "Serie B 2024-25"    53    63812
run "Serie B 2025-26"    53    79502

# -----------------------------------------------------------------------
# Ligue 2 (France)
# -----------------------------------------------------------------------
run "Ligue 2 2024-25"    182   61737
run "Ligue 2 2025-26"    182   77357

# -----------------------------------------------------------------------
# Romanian SuperLiga
# -----------------------------------------------------------------------
run "Romanian SuperLiga 2024-25"  152   62837
run "Romanian SuperLiga 2025-26"  152   77312

# -----------------------------------------------------------------------
# J1 League (Japan — calendar year seasons)
# -----------------------------------------------------------------------
run "J1 League 2025"     196   69871
run "J1 League 2026"     196   87931

echo ""
echo "=== BACKFILL COMPLETE: $(date) ==="
