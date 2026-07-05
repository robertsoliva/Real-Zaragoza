CREATE OR REPLACE TABLE `real-zaragoza-500608.rz_silver.silver_squad`
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY ingested_date DESC) AS rn
  FROM `real-zaragoza-500608.rz_bronze.bronze_squad`
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
