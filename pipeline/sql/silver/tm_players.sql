CREATE OR REPLACE TABLE `real-zaragoza-500608.silver.tm_players`
OPTIONS(description="GRAIN: one row per (player_id, club_id, season_id) — latest ingestion only. SOURCE: bronze.tm_players → raw.transfermarkt_players (quarterly scrape). DEDUP: ROW_NUMBER() OVER (PARTITION BY player_id, club_id, season_id ORDER BY ingested_date DESC). NOTES: rows with NULL player_id excluded. market_value_eur and contract_expiry may be NULL for lower-profile players. TM position is more granular than SofaScore (e.g. 'Centre-Back' vs 'D'). For historical value tracking across multiple scrapes, use gold.agg_tm_player_valuations instead. CLUSTER BY league_name, season_id.")
CLUSTER BY league_name, season_id
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY player_id, club_id, season_id
      ORDER BY ingested_date DESC
    ) AS rn
  FROM `real-zaragoza-500608.bronze.tm_players`
  WHERE player_id IS NOT NULL
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
