{{ config(cluster_by=['league_name', 'season_id', 'primary_position']) }}

SELECT
  league_name,
  tournament_id,
  season_id,
  primary_position,
  COUNT(DISTINCT player_id)            AS player_count,
  ROUND(AVG(avg_rating), 2)            AS avg_rating,
  ROUND(AVG(goals_p90), 3)             AS avg_goals_p90,
  ROUND(AVG(assists_p90), 3)           AS avg_assists_p90,
  ROUND(AVG(shots_p90), 3)             AS avg_shots_p90,
  ROUND(AVG(avg_xg_per_match), 3)      AS avg_xg_per_match,
  ROUND(AVG(key_passes_p90), 3)        AS avg_key_passes_p90,
  ROUND(AVG(pass_acc_pct), 1)          AS avg_pass_acc_pct,
  ROUND(AVG(tackles_p90), 3)           AS avg_tackles_p90,
  ROUND(AVG(interceptions_p90), 3)     AS avg_interceptions_p90,
  ROUND(AVG(aerial_win_pct), 1)        AS avg_aerial_win_pct,
  ROUND(AVG(duel_win_pct), 1)          AS avg_duel_win_pct,
  ROUND(AVG(touches_p90), 2)           AS avg_touches_p90,
  ROUND(AVG(yellows_p90), 3)           AS avg_yellows_p90
FROM {{ ref('fct_player_season_stats') }}
WHERE total_minutes >= 450
GROUP BY league_name, tournament_id, season_id, primary_position
