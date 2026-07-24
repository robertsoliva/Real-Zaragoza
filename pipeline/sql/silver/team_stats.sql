CREATE OR REPLACE TABLE `real-zaragoza-500608.silver.team_stats`
OPTIONS(description="Deduplicated SofaScore per-team per-match stats. One row per (match_id, team_id), latest ingestion wins. Partitioned by match_date, clustered by tournament_id and team_id.")
PARTITION BY match_date
CLUSTER BY tournament_id, team_id
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY match_id, team_id ORDER BY ingested_at DESC) AS rn
  FROM `real-zaragoza-500608.bronze.team_stats`
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
