CREATE OR REPLACE VIEW `real-zaragoza-500608.bronze.matches`
OPTIONS(description="GRAIN: one row per (match, scrape run) — NOT deduplicated; a match rescraped twice appears twice. SOURCE: UNION ALL of raw.sofascore_matches (all pipeline leagues) and wc_2026.sofascore_matches (FIFA WC 2026, tournament_id=16). Adds dataset_source ('standard' or 'wc_26') to distinguish origin. NOTES: no deduplication here — use silver.matches for one-row-per-match data. No partition. No cluster.")
AS
SELECT
  match_id, match_date, match_round, tournament_id, season_id, league_name,
  home_team_id, home_team_name, away_team_id, away_team_name,
  home_score, away_score, status, ingested_date, ingested_at,
  "standard" AS dataset_source
FROM `real-zaragoza-500608.raw.sofascore_matches`
UNION ALL
SELECT
  match_id, match_date, match_round, tournament_id, season_id, league_name,
  home_team_id, home_team_name, away_team_id, away_team_name,
  home_score, away_score, status, ingested_date, ingested_at,
  "wc_26" AS dataset_source
FROM `real-zaragoza-500608.wc_2026.sofascore_matches`
