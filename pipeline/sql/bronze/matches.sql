CREATE OR REPLACE VIEW `real-zaragoza-500608.bronze.matches`
OPTIONS(description="UNION ALL of match records from raw.sofascore_matches (standard leagues) and wc_2026.sofascore_matches (FIFA World Cup 2026). Adds dataset_source column to distinguish origin. Bronze layer — no deduplication applied here.")
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
