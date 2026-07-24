-- Historical market value snapshots per player per ingestion date.
-- Reads from raw (not silver) to preserve every quarterly scrape.
-- Use this table to track value evolution over time; silver.tm_players
-- deduplicates to latest-only and is not suitable for trend analysis.
CREATE OR REPLACE TABLE `real-zaragoza-500608.gold.agg_tm_player_valuations`
CLUSTER BY player_id, league_name
AS
SELECT
  player_id,
  name                                         AS player_name,
  club_id,
  club_name,
  league_name,
  season_id,
  position,
  age,
  nationality,
  market_value_eur,
  contract_expiry,
  ingested_date,
  ROW_NUMBER() OVER (
    PARTITION BY player_id, club_id, season_id
    ORDER BY ingested_date DESC
  )                                            AS snapshot_rank
FROM `real-zaragoza-500608.raw.transfermarkt_players`
WHERE market_value_eur IS NOT NULL
