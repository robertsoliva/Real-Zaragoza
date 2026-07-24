CREATE OR REPLACE TABLE `real-zaragoza-500608.gold.agg_player_market_values`
OPTIONS(description="GRAIN: one row per (player_id, club_id, season_id) — latest quarterly TM scrape. SOURCE: silver.tm_players (deduped TM data). NOTES: TM position is the source of truth for scouting — more granular than SofaScore (e.g. 'Centre-Back' vs 'D', 'Left Winger' vs 'F'). market_value_eur is Transfermarkt's estimated value in EUR (may be NULL for lower-profile players). contract_expiry is the contract end date. For historical market value evolution across scrapes, use agg_tm_player_valuations. CLUSTER BY league_name, position, season_id.")
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
