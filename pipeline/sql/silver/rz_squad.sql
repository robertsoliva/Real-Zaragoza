CREATE OR REPLACE TABLE `real-zaragoza-500608.silver.rz_squad`
OPTIONS(description="GRAIN: one row per player_id — latest ingestion only. SOURCE: bronze.rz_squad → raw.transfermarkt_squad (Zaragoza-only scraper). DEDUP: ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY ingested_date DESC), keeps rn=1. NOTES: single-club table; use gold.agg_rz_squad_finances for the finance/contract view sorted by value. No partition. No cluster.")
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY ingested_date DESC) AS rn
  FROM `real-zaragoza-500608.bronze.rz_squad`
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
