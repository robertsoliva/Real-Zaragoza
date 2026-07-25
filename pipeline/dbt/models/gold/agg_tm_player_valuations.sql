{{ config(cluster_by=['player_id', 'league_name']) }}

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
FROM {{ source('raw', 'transfermarkt_players') }}
WHERE market_value_eur IS NOT NULL
