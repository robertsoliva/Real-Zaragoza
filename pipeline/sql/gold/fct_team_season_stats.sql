CREATE OR REPLACE TABLE `real-zaragoza-500608.gold.fct_team_season_stats`
CLUSTER BY league_name, season_id
AS
SELECT
  team_id, team_name, league_name, dataset_source, tournament_id, season_id,
  COUNT(DISTINCT match_id)                                                                    AS matches,
  ROUND(AVG(possession_pct), 1)                                                               AS avg_possession,
  ROUND(AVG(total_passes), 0)                                                                 AS avg_passes,
  ROUND(SAFE_DIVIDE(AVG(accurate_passes), AVG(total_passes)) * 100, 1)                       AS avg_pass_acc_pct,
  ROUND(AVG(total_shots), 1)                                                                  AS avg_shots,
  ROUND(AVG(shots_on_target), 1)                                                              AS avg_sot,
  ROUND(AVG(total_tackles), 1)                                                                AS avg_tackles,
  ROUND(AVG(interceptions), 1)                                                                AS avg_interceptions,
  ROUND(AVG(corners), 1)                                                                      AS avg_corners,
  ROUND(AVG(fouls), 1)                                                                        AS avg_fouls,
  ROUND(AVG(yellow_cards), 2)                                                                 AS avg_yellows,
  ROUND(AVG(big_chances), 1)                                                                  AS avg_big_chances,
  ROUND(AVG(dribbles_completed), 1)                                                           AS avg_dribbles_completed,
  ROUND(AVG(aerial_duels_won), 1)                                                             AS avg_aerial_won,
  ROUND(AVG(SAFE_DIVIDE(aerial_duels_won, total_aerial_duels)) * 100, 1)                     AS avg_aerial_win_pct
FROM `real-zaragoza-500608.silver.team_stats`
GROUP BY 1,2,3,4,5,6
