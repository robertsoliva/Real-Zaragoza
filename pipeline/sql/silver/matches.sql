CREATE OR REPLACE TABLE `real-zaragoza-500608.rz_silver.matches`
PARTITION BY match_date
CLUSTER BY tournament_id, match_round
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY ingested_at DESC) AS rn
  FROM `real-zaragoza-500608.rz_bronze.matches`
)
SELECT
  match_id, match_date, match_round, tournament_id, season_id, league_name, dataset_source,
  home_team_id, home_team_name, away_team_id, away_team_name,
  home_score, away_score, status
FROM ranked WHERE rn = 1
