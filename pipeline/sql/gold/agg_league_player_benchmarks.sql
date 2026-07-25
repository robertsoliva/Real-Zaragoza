-- Per-position per-league average stats. Use in scouting reports to contextualise
-- a player's numbers against the typical level in their league and position.
-- Min 450 min (5 full matches) to exclude fringe appearances.
CREATE OR REPLACE TABLE `real-zaragoza-500608.gold.agg_league_player_benchmarks`
CLUSTER BY league_name, season_id, primary_position
OPTIONS(description="GRAIN: one row per (league_name, season_id, primary_position) — average per-90 and percentage stats across all qualifying players. SOURCE: gold.fct_player_season_stats. FILTER: total_minutes >= 450 (approximately 5 full matches) to exclude fringe appearances from skewing averages. NOTES: position uses SofaScore codes (G/D/M/F). Use to contextualise individual player stats: compare player's goals_p90 against avg_goals_p90 for their position and league. CLUSTER BY league_name, season_id, primary_position.")
AS
SELECT
  league_name,
  tournament_id,
  season_id,
  primary_position,
  COUNT(DISTINCT player_id)                AS player_count,
  ROUND(AVG(avg_rating), 2)               AS avg_rating,
  ROUND(AVG(goals_p90), 3)               AS avg_goals_p90,
  ROUND(AVG(assists_p90), 3)             AS avg_assists_p90,
  ROUND(AVG(shots_p90), 3)              AS avg_shots_p90,
  ROUND(AVG(avg_xg_per_match), 3)        AS avg_xg_per_match,
  ROUND(AVG(key_passes_p90), 3)          AS avg_key_passes_p90,
  ROUND(AVG(pass_acc_pct), 1)           AS avg_pass_acc_pct,
  ROUND(AVG(tackles_p90), 3)            AS avg_tackles_p90,
  ROUND(AVG(interceptions_p90), 3)      AS avg_interceptions_p90,
  ROUND(AVG(aerial_win_pct), 1)         AS avg_aerial_win_pct,
  ROUND(AVG(duel_win_pct), 1)           AS avg_duel_win_pct,
  ROUND(AVG(touches_p90), 2)            AS avg_touches_p90,
  ROUND(AVG(yellows_p90), 3)            AS avg_yellows_p90
FROM `real-zaragoza-500608.gold.fct_player_season_stats`
WHERE total_minutes >= 450
GROUP BY league_name, tournament_id, season_id, primary_position
