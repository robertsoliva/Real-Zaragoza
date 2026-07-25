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
FROM {{ ref('silver_rz_squad') }}
ORDER BY market_value_eur DESC NULLS LAST
