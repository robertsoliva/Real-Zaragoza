{{ config(cluster_by=['league_name', 'position', 'season_id']) }}

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
FROM {{ ref('silver_tm_players') }}
