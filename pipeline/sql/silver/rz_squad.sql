CREATE OR REPLACE TABLE `real-zaragoza-500608.rz_silver.rz_squad`
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY ingested_date DESC) AS rn
  FROM `real-zaragoza-500608.rz_bronze.rz_squad`
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
