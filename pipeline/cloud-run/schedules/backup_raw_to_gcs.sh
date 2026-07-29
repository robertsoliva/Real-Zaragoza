#!/bin/bash
# Export all raw BQ tables to GCS as Parquet (daily snapshot, overwrites same-day path).
# Called by run_next_from_queue.sh after each SofaScore extraction.
# One snapshot per calendar day — 6 extractions/day all overwrite the same date path.
#
# Bucket must exist: gsutil mb -p real-zaragoza-500608 -l europe-west1 gs://rz-raw-backups
# Restore: bq load --source_format=PARQUET PROJECT:DATASET.TABLE 'gs://rz-raw-backups/DATE/dataset/table/*.parquet'

set -euo pipefail

BUCKET="gs://rz-raw-backups"
DATE=$(date +%Y-%m-%d)
PROJECT="real-zaragoza-500608"
BQ=/opt/homebrew/bin/bq

TABLES=(
    "raw.sofascore_matches"
    "raw.sofascore_player_match_stats"
    "raw.sofascore_shots"
    "raw.sofascore_team_match_stats"
    "raw.transfermarkt_players"
    "raw.capology_wages"
    "raw.bqml_wage_predictions"
    "wc_2026.sofascore_matches"
    "wc_2026.sofascore_player_match_stats"
    "wc_2026.sofascore_shots"
    "wc_2026.sofascore_team_match_stats"
)

echo "[$(date '+%Y-%m-%d %H:%M:%S')] GCS backup → $BUCKET/$DATE/"

for full_table in "${TABLES[@]}"; do
    dataset=$(echo "$full_table" | cut -d. -f1)
    table=$(echo "$full_table" | cut -d. -f2)
    dest="$BUCKET/$DATE/$dataset/$table/*.parquet"
    echo "  $full_table → $dest"
    $BQ extract \
        --project_id="$PROJECT" \
        --destination_format=PARQUET \
        --compression=SNAPPY \
        "$PROJECT:$full_table" \
        "$dest" \
        || echo "  WARN: skipped $full_table (table may not exist yet)"
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] GCS backup complete"
