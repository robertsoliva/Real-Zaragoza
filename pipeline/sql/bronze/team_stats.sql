CREATE OR REPLACE VIEW `real-zaragoza-500608.bronze.team_stats`
OPTIONS(description="GRAIN: one row per (team, match, scrape run) — NOT deduplicated; two rows per match (one per side). SOURCE: UNION ALL of raw.sofascore_team_match_stats + wc_2026.sofascore_team_match_stats. Adds dataset_source ('standard' or 'wc_26'). NOTES: includes detailed match stats — shots, passes, tackles, aerial duels, dribbles, corners, big chances. No partition. No cluster.")
AS
SELECT
  match_id, match_date, match_round, tournament_id, season_id, league_name,
  team_id, team_name, side, possession_pct, total_shots, shots_on_target,
  shots_off_target, blocked_shots, shots_on_woodwork, shots_inside_box, shots_outside_box,
  big_chances, big_chances_scored, big_chances_missed, corners, offsides, fouls,
  yellow_cards, red_cards, total_passes, accurate_passes, accurate_long_balls, total_long_balls,
  accurate_crosses, total_crosses, touches_in_opp_box, final_third_entries, final_third_acc,
  final_third_total, total_tackles, won_tackles, interceptions, clearances, ball_recoveries,
  errors_leading_to_shot, goalkeeper_saves, ground_duels_won, total_ground_duels,
  aerial_duels_won, total_aerial_duels, dribbles_completed, total_dribbles, dispossessed,
  ingested_date, ingested_at, "standard" AS dataset_source
FROM `real-zaragoza-500608.raw.sofascore_team_match_stats`
UNION ALL
SELECT
  match_id, match_date, match_round, tournament_id, season_id, league_name,
  team_id, team_name, side, possession_pct, total_shots, shots_on_target,
  shots_off_target, blocked_shots, shots_on_woodwork, shots_inside_box, shots_outside_box,
  big_chances, big_chances_scored, big_chances_missed, corners, offsides, fouls,
  yellow_cards, red_cards, total_passes, accurate_passes, accurate_long_balls, total_long_balls,
  accurate_crosses, total_crosses, touches_in_opp_box, final_third_entries, final_third_acc,
  final_third_total, total_tackles, won_tackles, interceptions, clearances, ball_recoveries,
  errors_leading_to_shot, goalkeeper_saves, ground_duels_won, total_ground_duels,
  aerial_duels_won, total_aerial_duels, dribbles_completed, total_dribbles, dispossessed,
  ingested_date, ingested_at, "wc_26" AS dataset_source
FROM `real-zaragoza-500608.wc_2026.sofascore_team_match_stats`
