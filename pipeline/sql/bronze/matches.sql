CREATE OR REPLACE VIEW `real-zaragoza-500608.rz_bronze.matches` AS
SELECT
  match_id, match_date, match_round, tournament_id, season_id, league_name,
  home_team_id, home_team_name, away_team_id, away_team_name,
  home_score, away_score, status, ingested_date, ingested_at,
  "standard" AS dataset_source
FROM `real-zaragoza-500608.rz_raw.sofascore_matches`
UNION ALL
SELECT
  match_id, match_date, match_round, tournament_id, season_id, league_name,
  home_team_id, home_team_name, away_team_id, away_team_name,
  home_score, away_score, status, ingested_date, ingested_at,
  "wc_26" AS dataset_source
FROM `real-zaragoza-500608.WC_26.sofascore_matches`
