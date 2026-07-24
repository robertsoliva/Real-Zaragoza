CREATE OR REPLACE TABLE `real-zaragoza-500608.silver.matches`
OPTIONS(description="GRAIN: one row per match_id — latest ingestion only. SOURCE: bronze.matches (UNION ALL of raw + wc_2026). DEDUP: ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY ingested_at DESC). NOTES: covers all active pipeline leagues plus FIFA WC 2026 (dataset_source='wc_26'). Canonical join key for silver.player_stats and silver.team_stats. PARTITION BY match_date (DAY). CLUSTER BY tournament_id, match_round.")
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
