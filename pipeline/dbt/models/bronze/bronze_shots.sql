{{ config(alias='shots') }}

SELECT
  shot_id, match_id, match_date, match_round, tournament_id, season_id,
  CASE tournament_id WHEN '35' THEN 'Bundesliga' WHEN '44' THEN '2. Bundesliga' ELSE league_name END AS league_name,
  player_id, player_name, is_home, minute, added_time, time_seconds,
  x, y, goal_mouth_x, goal_mouth_y, goal_mouth_z, goal_mouth_location,
  block_x, block_y, body_part, shot_type, situation, xg,
  ingested_date, ingested_at, 'standard' AS dataset_source
FROM {{ source('raw', 'sofascore_shots') }}

UNION ALL

SELECT
  shot_id, match_id, match_date, match_round, tournament_id, season_id,
  CASE tournament_id WHEN '35' THEN 'Bundesliga' WHEN '44' THEN '2. Bundesliga' ELSE league_name END AS league_name,
  player_id, player_name, is_home, minute, added_time, time_seconds,
  x, y, goal_mouth_x, goal_mouth_y, goal_mouth_z, goal_mouth_location,
  block_x, block_y, body_part, shot_type, situation, xg,
  ingested_date, ingested_at, 'wc_26' AS dataset_source
FROM {{ source('wc_2026', 'sofascore_shots') }}
