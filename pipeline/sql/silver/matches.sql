CREATE OR REPLACE TABLE `real-zaragoza-500608.silver.matches`
OPTIONS(description="Deduplicated SofaScore match records covering all pipeline leagues plus WC 2026. One row per match_id (latest ingestion). Partitioned by match_date, clustered by tournament_id and match_round.")
PARTITION BY match_date
CLUSTER BY tournament_id, match_round
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY ingested_at DESC) AS rn
  FROM `real-zaragoza-500608.bronze.matches`
)
SELECT
  match_id, match_date, match_round, tournament_id, season_id, league_name, dataset_source,
  home_team_id, home_team_name, away_team_id, away_team_name,
  home_score, away_score, status
FROM ranked WHERE rn = 1
