CREATE OR REPLACE VIEW `real-zaragoza-500608.bronze.matches` AS
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
