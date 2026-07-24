"""
Real Zaragoza — processed-layer refresh job.

Runs all bronze→silver→gold SQL files against BigQuery in dependency order.
Designed to run as a Cloud Run Job, triggered daily by Cloud Scheduler.

Exit 0 on full success, exit 1 if any model fails (Cloud Run will mark the
task as failed and retry according to the job's retry policy).
"""

import os
import sys
from pathlib import Path

from google.cloud import bigquery

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "real-zaragoza-500608")
SQL_DIR = Path("/app/sql")

# Execution order matters: bronze (views) → silver (tables) → gold (tables).
# Silver/gold models reference bronze via CREATE OR REPLACE, so bronze must run first.
SQL_ORDER = [
    # Bronze — lightweight views, always recreated first
    "bronze/bronze_squad.sql",
    "bronze/bronze_tm_players.sql",
    "bronze/bronze_matches.sql",
    "bronze/bronze_player_stats.sql",
    "bronze/bronze_shots.sql",
    "bronze/bronze_team_stats.sql",
    # Silver — dedup tables (latest row per natural key)
    "silver/silver_squad.sql",
    "silver/silver_tm_players.sql",
    "silver/silver_matches.sql",
    "silver/silver_player_stats.sql",
    "silver/silver_shots.sql",
    "silver/silver_team_stats.sql",
    # Gold — aggregated scouting/analysis tables
    "gold/gold_player_season.sql",
    "gold/gold_team_season.sql",
    "gold/gold_tm_players.sql",
    "gold/gold_zaragoza_matches.sql",
]


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    ok: list[str] = []
    failed: list[str] = []

    for rel_path in SQL_ORDER:
        full_path = SQL_DIR / rel_path
        if not full_path.exists():
            print(f"WARN  {rel_path} not found — skipping", flush=True)
            continue

        sql = full_path.read_text()
        print(f"RUN   {rel_path}", flush=True)
        try:
            job = client.query(sql)
            job.result()
            print(f"OK    {rel_path}", flush=True)
            ok.append(rel_path)
        except Exception as exc:
            print(f"FAIL  {rel_path}: {exc}", flush=True)
            failed.append(rel_path)

    print(f"\n{len(ok)} succeeded, {len(failed)} failed.", flush=True)
    if failed:
        print(f"Failed models: {failed}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
