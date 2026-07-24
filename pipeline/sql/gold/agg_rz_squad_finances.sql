-- Zaragoza squad financial and contract snapshot (latest Transfermarkt scrape).
-- Source: rz_silver.rz_squad (Zaragoza-only single-club TM scraper).
-- Use for wage/value planning, contract expiry alerts, and squad cost analysis.
CREATE OR REPLACE TABLE `real-zaragoza-500608.rz_gold.agg_rz_squad_finances`
AS
SELECT
  player_id,
  name,
  jersey_number,
  position,
  age,
  date_of_birth,
  nationality,
  height,
  foot,
  market_value_eur,
  contract_expiry,
  joined_date,
  signed_from,
  signing_fee,
  season_id,
  ingested_date
FROM `real-zaragoza-500608.rz_silver.rz_squad`
ORDER BY market_value_eur DESC NULLS LAST
