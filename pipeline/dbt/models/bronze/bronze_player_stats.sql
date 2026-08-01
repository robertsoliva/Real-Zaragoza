{{ config(alias='player_stats') }}

SELECT
  match_id, player_id, match_date, match_round, tournament_id, season_id,
  CASE tournament_id WHEN '35' THEN 'Bundesliga' WHEN '44' THEN '2. Bundesliga'
    WHEN '17' THEN 'Premier League' WHEN '8' THEN 'La Liga' WHEN '23' THEN 'Serie A' WHEN '34' THEN 'Ligue 1'
    ELSE league_name END AS league_name,
  player_name, team_id, team_name, is_home, position, shirt_number, is_substitute, captain,
  minutes_played, goals, goal_assists, rating, total_passes, accurate_passes,
  total_long_balls, accurate_long_balls, total_crosses, accurate_crosses, key_passes,
  total_shots, shots_on_target, aerial_won, aerial_lost, duel_won, duel_lost, challenge_lost,
  total_tackle, won_tackle, interceptions, total_clearance, ball_recovery, dispossessed,
  was_fouled, fouls, touches, possession_lost, unsuccessful_touch,
  yellow_cards, red_cards, saves, expected_goals, expected_assists,
  ingested_date, ingested_at, 'standard' AS dataset_source
FROM {{ source('raw', 'sofascore_player_match_stats') }}

UNION ALL

SELECT
  match_id, player_id, match_date, match_round, tournament_id, season_id,
  CASE tournament_id WHEN '35' THEN 'Bundesliga' WHEN '44' THEN '2. Bundesliga'
    WHEN '17' THEN 'Premier League' WHEN '8' THEN 'La Liga' WHEN '23' THEN 'Serie A' WHEN '34' THEN 'Ligue 1'
    ELSE league_name END AS league_name,
  player_name, team_id, team_name, is_home, position, shirt_number, is_substitute, captain,
  minutes_played, goals, goal_assists, rating, total_passes, accurate_passes,
  total_long_balls, accurate_long_balls, total_crosses, accurate_crosses, key_passes,
  total_shots, shots_on_target, aerial_won, aerial_lost, duel_won, duel_lost, challenge_lost,
  total_tackle, won_tackle, interceptions, total_clearance, ball_recovery, dispossessed,
  was_fouled, fouls, touches, possession_lost, unsuccessful_touch,
  yellow_cards, red_cards, saves, expected_goals, expected_assists,
  ingested_date, ingested_at, 'wc_26' AS dataset_source
FROM {{ source('wc_2026', 'sofascore_player_match_stats') }}
