CREATE OR REPLACE TABLE `real-zaragoza-500608.silver.team_stats`
PARTITION BY match_date
CLUSTER BY tournament_id, team_id
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY match_id, team_id ORDER BY ingested_at DESC) AS rn
  FROM `real-zaragoza-500608.bronze.team_stats`
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
