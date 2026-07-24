CREATE OR REPLACE TABLE `real-zaragoza-500608.rz_silver.tm_players`
CLUSTER BY league_name, season_id
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY player_id, club_id, season_id
      ORDER BY ingested_date DESC
    ) AS rn
  FROM `real-zaragoza-500608.rz_bronze.tm_players`
  WHERE player_id IS NOT NULL
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
