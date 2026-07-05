#!/bin/bash
# Materialises rz_silver and rz_gold tables from rz_bronze views.
# Run after each extraction slot (see launchd plists: refresh-11am, refresh-8pm).
# rz_bronze views are live — no refresh needed.
# Order matters: silver_matches must finish before player_stats and shots.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
SQL="$REPO/pipeline/sql"
LOG="/tmp/rz_refresh_processed_$(date +%Y%m%d_%H%M%S).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting rz_silver / rz_gold refresh" | tee -a "$LOG"

# --- Silver: matches first (player_stats and shots JOIN to it) ---
echo "[$(date '+%Y-%m-%d %H:%M:%S')] silver_matches..." | tee -a "$LOG"
bq query --use_legacy_sql=false "$(cat "$SQL/silver/silver_matches.sql")" >> "$LOG" 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] silver_matches done" | tee -a "$LOG"

# --- Silver: remaining four in parallel ---
echo "[$(date '+%Y-%m-%d %H:%M:%S')] silver player_stats / team_stats / shots / squad (parallel)..." | tee -a "$LOG"
bq query --use_legacy_sql=false "$(cat "$SQL/silver/silver_player_stats.sql")" >> "$LOG" 2>&1 &
bq query --use_legacy_sql=false "$(cat "$SQL/silver/silver_team_stats.sql")"   >> "$LOG" 2>&1 &
bq query --use_legacy_sql=false "$(cat "$SQL/silver/silver_shots.sql")"        >> "$LOG" 2>&1 &
bq query --use_legacy_sql=false "$(cat "$SQL/silver/silver_squad.sql")"        >> "$LOG" 2>&1 &
wait
echo "[$(date '+%Y-%m-%d %H:%M:%S')] silver layer done" | tee -a "$LOG"

# --- Gold: all three in parallel ---
echo "[$(date '+%Y-%m-%d %H:%M:%S')] gold player_season / team_season / zaragoza_matches (parallel)..." | tee -a "$LOG"
bq query --use_legacy_sql=false "$(cat "$SQL/gold/gold_player_season.sql")"      >> "$LOG" 2>&1 &
bq query --use_legacy_sql=false "$(cat "$SQL/gold/gold_team_season.sql")"        >> "$LOG" 2>&1 &
bq query --use_legacy_sql=false "$(cat "$SQL/gold/gold_zaragoza_matches.sql")"   >> "$LOG" 2>&1 &
wait
echo "[$(date '+%Y-%m-%d %H:%M:%S')] gold layer done" | tee -a "$LOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Refresh complete. Log: $LOG"
