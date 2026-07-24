"""
Real Zaragoza — processed-layer refresh job.

Runs all bronze→silver→gold SQL files against BigQuery in dependency order,
then sets table-level descriptions via the Python client (BQ silently drops
OPTIONS(description=...) from CTAS when placed before PARTITION/CLUSTER BY).

Designed to run as a Cloud Run Job, triggered daily by Cloud Scheduler.
Exit 0 on full success, exit 1 if any model fails.
"""

import os
import sys
from pathlib import Path

from google.cloud import bigquery

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "real-zaragoza-500608")
SQL_DIR = Path("/app/sql")

SQL_ORDER = [
    # Raw table descriptions (ALTER TABLE column descriptions — idempotent)
    "raw/sofascore_matches_descriptions.sql",
    "raw/sofascore_player_match_stats_descriptions.sql",
    "raw/sofascore_shots_descriptions.sql",
    "raw/sofascore_team_match_stats_descriptions.sql",
    "raw/transfermarkt_players_descriptions.sql",
    "raw/transfermarkt_squad_descriptions.sql",
    # WC 2026 table descriptions
    "wc_2026/sofascore_matches_descriptions.sql",
    "wc_2026/sofascore_player_match_stats_descriptions.sql",
    "wc_2026/sofascore_shots_descriptions.sql",
    "wc_2026/sofascore_team_match_stats_descriptions.sql",
    # Bronze views (always recreated first)
    "bronze/rz_squad.sql",
    "bronze/rz_squad_descriptions.sql",
    "bronze/tm_players.sql",
    "bronze/tm_players_descriptions.sql",
    "bronze/capology_wages.sql",
    "bronze/capology_wages_descriptions.sql",
    "bronze/matches.sql",
    "bronze/matches_descriptions.sql",
    "bronze/player_stats.sql",
    "bronze/player_stats_descriptions.sql",
    "bronze/shots.sql",
    "bronze/shots_descriptions.sql",
    "bronze/team_stats.sql",
    "bronze/team_stats_descriptions.sql",
    # Silver tables (dedup)
    "silver/rz_squad.sql",
    "silver/rz_squad_descriptions.sql",
    "silver/tm_players.sql",
    "silver/tm_players_descriptions.sql",
    "silver/capology_wages.sql",
    "silver/capology_wages_descriptions.sql",
    "silver/matches.sql",
    "silver/matches_descriptions.sql",
    "silver/player_stats.sql",
    "silver/player_stats_descriptions.sql",
    "silver/shots.sql",
    "silver/shots_descriptions.sql",
    "silver/team_stats.sql",
    "silver/team_stats_descriptions.sql",
    # Gold tables (aggregated)
    "gold/fct_player_season_stats.sql",
    "gold/fct_player_season_stats_descriptions.sql",
    "gold/fct_team_season_stats.sql",
    "gold/fct_team_season_stats_descriptions.sql",
    "gold/fct_rz_matches.sql",
    "gold/fct_rz_matches_descriptions.sql",
    "gold/agg_player_market_values.sql",
    "gold/agg_player_market_values_descriptions.sql",
    "gold/agg_scouting_player_season.sql",
    "gold/agg_scouting_player_season_descriptions.sql",
    "gold/agg_rz_squad_finances.sql",
    "gold/agg_rz_squad_finances_descriptions.sql",
    "gold/agg_league_player_benchmarks.sql",
    "gold/agg_league_player_benchmarks_descriptions.sql",
    "gold/agg_tm_player_valuations.sql",
    "gold/agg_tm_player_valuations_descriptions.sql",
    "gold/agg_player_wage_benchmarks.sql",
    "gold/agg_player_wage_benchmarks_descriptions.sql",
]

# Table-level descriptions applied via Python client after SQL runs.
# BQ silently ignores OPTIONS(description=...) in CTAS when placed before
# PARTITION BY / CLUSTER BY — setting via update_table() is reliable.
TABLE_DESCRIPTIONS = {
    "bronze.rz_squad": (
        "GRAIN: one row per player per ingestion run (NOT deduplicated). "
        "Pass-through view of raw.transfermarkt_squad. Zaragoza-only TM squad data: "
        "name, position, age, market value, contract, nationality. No partition. No cluster. "
        "SOURCE: Zaragoza-specific TM squad scraper (scraper_transfermarkt.py)."
    ),
    "bronze.tm_players": (
        "GRAIN: one row per (player, club, ingestion run) — NOT deduplicated. "
        "Pass-through view of raw.transfermarkt_players. Multi-league TM data across 19 "
        "active pipeline leagues (1RFEF excluded — too many clubs). No partition. No cluster. "
        "SOURCE: scraper_transfermarkt_leagues.py, quarterly."
    ),
    "bronze.capology_wages": (
        "GRAIN: one row per (player, club, ingestion run) — NOT deduplicated. "
        "Pass-through view of raw.capology_wages. Gross wage data for ~2500 players across "
        "top 5 EU leagues (Premier League, La Liga, Bundesliga, Ligue 1, Serie A). "
        "Loan player filtering happens at silver. No partition. No cluster. "
        "SOURCE: scraper_capology.py, monthly."
    ),
    "bronze.matches": (
        "GRAIN: one row per (match, scrape run) — NOT deduplicated. "
        "UNION ALL of raw.sofascore_matches (all pipeline leagues) + wc_2026.sofascore_matches "
        "(FIFA WC 2026). Adds dataset_source tag ('standard' or 'wc_26'). "
        "No deduplication — use silver.matches for one-row-per-match data. No partition. No cluster."
    ),
    "bronze.player_stats": (
        "GRAIN: one row per (player, match, scrape run) — NOT deduplicated. "
        "UNION ALL of player match stats from raw + wc_2026. ~40 per-match stats per player. "
        "No partition. No cluster. SOURCE: sofascore_player_match_stats tables."
    ),
    "bronze.shots": (
        "GRAIN: one row per (shot, scrape run) — NOT deduplicated. "
        "UNION ALL of shot events from raw + wc_2026. Each row is one shot attempt with "
        "spatial coordinates and xG. No partition. No cluster."
    ),
    "bronze.team_stats": (
        "GRAIN: one row per (team, match, scrape run) — NOT deduplicated. "
        "UNION ALL of team match stats from raw + wc_2026. Aggregated team-level stats per match. "
        "No partition. No cluster."
    ),
    "silver.rz_squad": (
        "GRAIN: one row per player — latest ingestion snapshot only. "
        "Deduplicated Zaragoza TM squad data (ROW_NUMBER by player_id, latest ingested_at wins). "
        "SOURCE: bronze.rz_squad. No partition. No cluster."
    ),
    "silver.tm_players": (
        "GRAIN: one row per (player_id, club_id, season_id) — latest ingestion. "
        "Deduplicated multi-league TM data. ROW_NUMBER PARTITION BY (player_id, club_id, season_id) "
        "ORDER BY ingested_date DESC. NOTES: market_value_eur and contract_expiry may be NULL for "
        "lower-profile players. CLUSTER BY league_name, season_id. SOURCE: bronze.tm_players."
    ),
    "silver.capology_wages": (
        "GRAIN: one row per (player_name, club_name, league_name) — latest ingestion. "
        "Deduplicated Capology wages; loan players excluded to avoid wage distortion at parent club. "
        "Adds wage_eur_annual = wage_eur_weekly × 52. "
        "CLUSTER BY league_name, position_group. SOURCE: bronze.capology_wages."
    ),
    "silver.matches": (
        "GRAIN: one row per match_id — latest ingestion only. "
        "Deduplicated SofaScore matches (ROW_NUMBER PARTITION BY match_id ORDER BY ingested_at DESC). "
        "Canonical join key for silver.player_stats and silver.team_stats. "
        "PARTITION BY match_date (DAY). CLUSTER BY tournament_id, match_round. "
        "Covers all pipeline leagues + FIFA WC 2026 (dataset_source='wc_26')."
    ),
    "silver.player_stats": (
        "GRAIN: one row per (player_id, match_id) — latest ingestion only. "
        "Deduplicated player match stats. Joined with silver.matches to inherit match_date "
        "(enables date partition). FILTER: minutes_played > 0 applied in gold, not here. "
        "PARTITION BY match_date (DAY). CLUSTER BY tournament_id, team_id."
    ),
    "silver.shots": (
        "GRAIN: one row per shot_id — latest ingestion only. "
        "Deduplicated shot events. Joined with silver.matches for match_date partition. "
        "PARTITION BY match_date (DAY). CLUSTER BY tournament_id."
    ),
    "silver.team_stats": (
        "GRAIN: one row per (team_id, match_id) — latest ingestion only. "
        "Deduplicated team match stats. "
        "PARTITION BY match_date (DAY). CLUSTER BY tournament_id, team_id."
    ),
    "gold.fct_player_season_stats": (
        "GRAIN: one row per (player_id, team_name, league_name, dataset_source, tournament_id, season_id). "
        "Season totals and per-90 rates aggregated from silver.player_stats. "
        "FILTER: minutes_played > 0 applied before aggregation. "
        "NOTES: primary_position uses ANY_VALUE (SofaScore G/D/M/F code) — use TM position from "
        "agg_scouting_player_season for granular role mapping. Per-90 = stat / total_minutes × 90. "
        "CLUSTER BY league_name, season_id, primary_position. Primary scouting query target."
    ),
    "gold.fct_team_season_stats": (
        "GRAIN: one row per (team_id, team_name, league_name, dataset_source, tournament_id, season_id). "
        "Season averages per team aggregated from silver.team_stats. "
        "CLUSTER BY league_name, season_id. "
        "Use for team style comparison (possession, passes, shots, aerial stats)."
    ),
    "gold.fct_rz_matches": (
        "GRAIN: one row per match where Real Zaragoza (team_id='2815') played. "
        "Adds result (W/D/L), venue (home/away), rz_goals, opponent_goals, opponent. "
        "LEFT JOIN silver.team_stats to pull Zaragoza's per-match stats. "
        "PARTITION BY match_date (DAY). CLUSTER BY season_id, result."
    ),
    "gold.agg_player_market_values": (
        "GRAIN: one row per (player_id, club_id, season_id) — latest TM snapshot. "
        "Transfermarkt market values, contract data, and granular position per player+season. "
        "SOURCE: silver.tm_players. TM position is more granular than SofaScore "
        "(e.g. 'Centre-Back' vs 'D'). CLUSTER BY league_name, position, season_id."
    ),
    "gold.agg_scouting_player_season": (
        "GRAIN: one row per (player_id, team_name, league_name, dataset_source, tournament_id, season_id). "
        "Main scouting table: SofaScore season stats LEFT JOIN TM market value + position data. "
        "JOIN on normalised name + club + season — TM columns are NULL when join misses (~30-40% of rows). "
        "Use tm_position (TM, granular) over primary_position (SofaScore, broad) for positional analysis. "
        "CLUSTER BY league_name, season_id, tm_position."
    ),
    "gold.agg_rz_squad_finances": (
        "GRAIN: one row per player in the latest Zaragoza TM squad snapshot. "
        "Market values, contracts, and signing info for Zaragoza's current squad. "
        "SOURCE: silver.rz_squad, ordered by market_value_eur DESC. "
        "Use for squad financial overview and contract planning. No partition. No cluster."
    ),
    "gold.agg_league_player_benchmarks": (
        "GRAIN: one row per (league_name, season_id, primary_position). "
        "Average stats by position for contextualising individual player numbers. "
        "FILTER: players with >= 450 minutes only (avoids noise from fringe appearances). "
        "SOURCE: gold.fct_player_season_stats. "
        "CLUSTER BY league_name, season_id, primary_position."
    ),
    "gold.agg_tm_player_valuations": (
        "GRAIN: one row per (player_id, club_id, season_id, ingested_date) — ALL quarterly scrapes preserved. "
        "Reads raw.transfermarkt_players directly (NOT silver — silver deduplicates to latest). "
        "snapshot_rank=1 is the most recent snapshot per (player, club, season). "
        "Use for market value evolution and trend analysis across quarterly scrapes. "
        "CLUSTER BY player_id, league_name."
    ),
    "gold.agg_player_wage_benchmarks": (
        "GRAIN: one row per (league_name, position_group). "
        "Wage benchmarks aggregated from silver.capology_wages LEFT JOIN silver.tm_players. "
        "Provides P25/median/P75/avg annual gross wage and avg market value per league+position. "
        "NOTES: covers top 5 EU leagues only (Premier League, La Liga, Bundesliga, Ligue 1, Serie A) "
        "— does NOT cover the SofaScore pipeline leagues (LaLiga2, Serie B, etc.). "
        "CLUSTER BY league_name, position_group."
    ),
}


def set_table_descriptions(client: bigquery.Client) -> None:
    print("\nSetting table-level descriptions...", flush=True)
    for table_ref, desc in TABLE_DESCRIPTIONS.items():
        full_ref = f"{PROJECT_ID}.{table_ref}"
        try:
            table = client.get_table(full_ref)
            table.description = desc
            client.update_table(table, ["description"])
            print(f"DESC  {table_ref}", flush=True)
        except Exception as exc:
            print(f"WARN  {table_ref} description failed: {exc}", flush=True)


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

    set_table_descriptions(client)

    if failed:
        print(f"Failed models: {failed}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
