CREATE OR REPLACE VIEW `real-zaragoza-500608.bronze.player_stats`
OPTIONS(description="UNION ALL of per-player per-match stats from raw.sofascore_player_match_stats (standard leagues) and wc_2026.sofascore_player_match_stats (FIFA World Cup 2026). Adds dataset_source column. Bronze layer — no deduplication applied here.")
AS
SELECT
  match_id, player_id, match_date, match_round, tournament_id, season_id, league_name,
  player_name, team_id, team_name, is_home, position, shirt_number, is_substitute, captain,
  minutes_played, goals, goal_assists, rating, total_passes, accurate_passes,
  total_long_balls, accurate_long_balls, total_crosses, accurate_crosses, key_passes,
  total_shots, shots_on_target, aerial_won, aerial_lost, duel_won, duel_lost, challenge_lost,
  total_tackle, won_tackle, interceptions, total_clearance, ball_recovery, dispossessed,
  was_fouled, fouls, touches, possession_lost, unsuccessful_touch,
  yellow_cards, red_cards, saves, expected_goals, expected_assists,
  ingested_date, ingested_at, "standard" AS dataset_source
FROM `real-zaragoza-500608.raw.sofascore_player_match_stats`
UNION ALL
SELECT
  match_id, player_id, match_date, match_round, tournament_id, season_id, league_name,
  player_name, team_id, team_name, is_home, position, shirt_number, is_substitute, captain,
  minutes_played, goals, goal_assists, rating, total_passes, accurate_passes,
  total_long_balls, accurate_long_balls, total_crosses, accurate_crosses, key_passes,
  total_shots, shots_on_target, aerial_won, aerial_lost, duel_won, duel_lost, challenge_lost,
  total_tackle, won_tackle, interceptions, total_clearance, ball_recovery, dispossessed,
  was_fouled, fouls, touches, possession_lost, unsuccessful_touch,
  yellow_cards, red_cards, saves, expected_goals, expected_assists,
  ingested_date, ingested_at, "wc_26" AS dataset_source
FROM `real-zaragoza-500608.wc_2026.sofascore_player_match_stats`
