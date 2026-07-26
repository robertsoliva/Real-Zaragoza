{{ config(cluster_by=['league_name', 'season_id', 'tm_position']) }}

SELECT
  s.player_id                                                                AS sofascore_id,
  s.player_name,
  s.team_name,
  s.league_name,
  s.tournament_id,
  s.season_id,
  COALESCE(tm.position, s.primary_position)                                  AS tm_position,
  s.primary_position                                                          AS sofascore_position,
  s.matches,
  s.total_minutes,
  s.avg_rating,
  s.goals,
  s.assists,
  s.goals_p90,
  s.assists_p90,
  s.shots_p90,
  s.avg_xg_per_match,
  s.key_passes_p90,
  s.pass_acc_pct,
  s.long_ball_acc_pct,
  s.cross_acc_pct,
  s.tackles_p90,
  s.tackle_win_pct,
  s.interceptions_p90,
  s.clearances,
  s.aerial_win_pct,
  s.duel_win_pct,
  s.touches_p90,
  s.fouls_committed,
  s.yellows,
  s.yellows_p90,
  tm.player_id                                                               AS tm_player_id,
  tm.market_value_eur,
  tm.contract_expiry,
  tm.age,
  tm.date_of_birth,
  tm.nationality,
  tm.nationality_all,
  tm.height,
  tm.foot,
  tm.signed_from,
  tm.club_id                                                                 AS tm_club_id,
  COALESCE(cap.wage_eur_weekly,  pred.predicted_wage_eur_weekly)            AS wage_eur_weekly,
  COALESCE(cap.wage_eur_annual,  pred.predicted_wage_eur_annual)            AS wage_eur_annual,
  CASE
    WHEN cap.wage_eur_weekly         IS NOT NULL THEN 'capology_actual'
    WHEN pred.predicted_wage_eur_weekly IS NOT NULL THEN 'bqml_estimate'
    ELSE NULL
  END                                                                        AS wage_source
FROM {{ ref('fct_player_season_stats') }} s
LEFT JOIN {{ ref('agg_player_market_values') }} tm
  ON LOWER(TRIM(s.player_name))  = LOWER(TRIM(tm.name))
 AND LOWER(TRIM(s.team_name))   = LOWER(TRIM(tm.club_name))
 AND CAST(s.season_id AS STRING) = CAST(tm.season_id AS STRING)
LEFT JOIN {{ ref('silver_capology_wages') }} cap
  ON LOWER(TRIM(s.player_name)) = LOWER(TRIM(cap.player_name))
 AND LOWER(TRIM(s.team_name))   = LOWER(TRIM(cap.club_name))
LEFT JOIN {{ ref('silver_bqml_wages') }} pred
  ON LOWER(TRIM(s.player_name)) = LOWER(TRIM(pred.player_name))
 AND LOWER(TRIM(s.team_name))   = LOWER(TRIM(pred.club_name))
