CREATE OR REPLACE TABLE `real-zaragoza-500608.silver.rz_squad`
OPTIONS(description="Deduplicated Real Zaragoza squad from Transfermarkt. One row per player (latest ingestion). Source: bronze.rz_squad → raw.transfermarkt_squad.")
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY ingested_date DESC) AS rn
  FROM `real-zaragoza-500608.bronze.rz_squad`
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
