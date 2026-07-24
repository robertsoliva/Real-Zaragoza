CREATE OR REPLACE TABLE `real-zaragoza-500608.rz_silver.silver_tm_players` AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY player_id, club_id, season_id
      ORDER BY ingested_date DESC
    ) AS rn
  FROM `real-zaragoza-500608.rz_bronze.bronze_tm_players`
  WHERE player_id IS NOT NULL
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
