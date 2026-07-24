CREATE OR REPLACE TABLE `real-zaragoza-500608.gold.agg_player_market_values`
OPTIONS(description="Transfermarkt market value and contract data for all pipeline leagues, deduplicated to latest scrape per (player, club, season). Primary source of truth for market values, contract expiries, and TM position (more granular than SofaScore). Clustered by league_name, position, season_id.")
CLUSTER BY league_name, position, season_id
AS
SELECT
  player_id,
  name,
  club_id,
  club_name,
  club_slug,
  league_name,
  tm_league_code,
  season_id,
  position,
  age,
  date_of_birth,
  nationality,
  nationality_all,
  height,
  foot,
  market_value_eur,
  contract_expiry,
  joined_date,
  signed_from,
  signing_fee,
  jersey_number,
  ingested_date
FROM `real-zaragoza-500608.silver.tm_players`
