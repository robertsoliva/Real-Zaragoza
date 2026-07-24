CREATE OR REPLACE VIEW `real-zaragoza-500608.bronze.shots`
OPTIONS(description="GRAIN: one row per (shot_id, scrape run) — NOT deduplicated. SOURCE: UNION ALL of raw.sofascore_shots + wc_2026.sofascore_shots. Adds dataset_source ('standard' or 'wc_26'). NOTES: each row is a single shot attempt with pitch coordinates (x, y), goal-mouth coordinates, xG, body part, and shot type. team_id/team_name resolved at silver layer via JOIN with silver.matches using is_home flag. No partition. No cluster.")
AS
SELECT
  shot_id, match_id, match_date, match_round, tournament_id, season_id, league_name,
  player_id, player_name, is_home, minute, added_time, time_seconds,
  x, y, goal_mouth_x, goal_mouth_y, goal_mouth_z, goal_mouth_location,
  block_x, block_y, body_part, shot_type, situation, xg,
  ingested_date, ingested_at, "standard" AS dataset_source
FROM `real-zaragoza-500608.raw.sofascore_shots`
UNION ALL
SELECT
  shot_id, match_id, match_date, match_round, tournament_id, season_id, league_name,
  player_id, player_name, is_home, minute, added_time, time_seconds,
  x, y, goal_mouth_x, goal_mouth_y, goal_mouth_z, goal_mouth_location,
  block_x, block_y, body_part, shot_type, situation, xg,
  ingested_date, ingested_at, "wc_26" AS dataset_source
FROM `real-zaragoza-500608.wc_2026.sofascore_shots`
