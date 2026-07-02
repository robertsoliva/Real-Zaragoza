#!/bin/bash
# Retry backfill for the 9 seasons that failed due to IP rate-limiting on 2026-07-01.
# Order: Serie B → Ligue 2 → Romanian SuperLiga → J1 → 1RFEF last (structural issues to investigate).
#
# Inter-league pauses (15 min) prevent Cloudflare IP throttling that hit the original run.
# Within each league the two seasons run back-to-back (10s pause is fine).
#
# Usage:
#   caffeinate -i bash backfill_retry.sh
#   nohup caffeinate -i bash backfill_retry.sh > /tmp/sofascore_retry_$(date +%Y%m%d_%H%M).log 2>&1 &

set -euo pipefail

export GCP_PROJECT_ID=real-zaragoza-500608
PYTHON=/opt/anaconda3/bin/python3
SCRAPER=/Users/robertsoliva/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/scraper_sofascore.py
LEAGUE_PAUSE=900   # 15 minutes between different leagues

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
    sleep 10
}

pause_between_leagues() {
    echo ""
    echo "--- Pausing ${LEAGUE_PAUSE}s between leagues to avoid IP throttling ($(date)) ---"
    sleep "$LEAGUE_PAUSE"
    echo "--- Resuming at $(date) ---"
    echo ""
}

echo "=== RETRY BACKFILL STARTED: $(date) ==="
echo "9 seasons — Serie B, Ligue 2, Romanian SuperLiga, J1, then 1RFEF last."
echo "15-minute pause between each league group."
echo ""

# -----------------------------------------------------------------------
# Serie B (Italy)
# -----------------------------------------------------------------------
run "Serie B 2024-25"    53    63812
run "Serie B 2025-26"    53    79502

pause_between_leagues

# -----------------------------------------------------------------------
# Ligue 2 (France)
# -----------------------------------------------------------------------
run "Ligue 2 2024-25"    182   61737
run "Ligue 2 2025-26"    182   77357

pause_between_leagues

# -----------------------------------------------------------------------
# Romanian SuperLiga
# -----------------------------------------------------------------------
run "Romanian SuperLiga 2024-25"  152   62837
run "Romanian SuperLiga 2025-26"  152   77312

pause_between_leagues

# -----------------------------------------------------------------------
# J1 League (Japan — calendar year seasons)
# -----------------------------------------------------------------------
run "J1 League 2025"     196   69871
run "J1 League 2026"     196   87931

pause_between_leagues

# -----------------------------------------------------------------------
# 1RFEF — last (may have structural issues; investigate if low match counts)
# -----------------------------------------------------------------------
run "1RFEF 2024-25"      17073 64430
run "1RFEF 2025-26"      17073 77727

echo ""
echo "=== RETRY COMPLETE: $(date) ==="
