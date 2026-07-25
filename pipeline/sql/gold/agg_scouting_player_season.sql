-- Scouting-ready join of SofaScore season stats + Transfermarkt market value/contract data.
-- Join key: normalized player_name + team_name. Covers ~70-80% of players; some miss
-- due to naming differences between systems (e.g. accents, abbreviations).
-- TM position is the source of truth for position granularity (more detailed than SofaScore).
CREATE OR REPLACE TABLE `real-zaragoza-500608.gold.agg_scouting_player_season`
CLUSTER BY league_name, season_id, tm_position
OPTIONS(description="GRAIN: one row per (player_id, team_name, league_name, season_id) — SofaScore stats enriched with TM profile. SOURCE: gold.fct_player_season_stats LEFT JOIN gold.agg_player_market_values. JOIN KEY: LOWER(TRIM(player_name)) = LOWER(TRIM(name)) AND LOWER(TRIM(team_name)) = LOWER(TRIM(club_name)) AND CAST(season_id AS STRING). NOTES: LEFT JOIN — TM columns (market_value_eur, contract_expiry, tm_player_id, age, nationality, height, foot) are NULL when name/club doesn't match across systems (~20-30% miss rate due to diacritics and abbreviations). tm_position = COALESCE(TM position, SofaScore primary_position) — prefer tm_position for role mapping in 4-2-3-1. Primary table for scouting report data loading. CLUSTER BY league_name, season_id, tm_position.")
AS
SELECT
  s.player_id                                                                AS sofascore_id,
  s.player_name,
  s.team_name,
  s.league_name,
  s.tournament_id,
  s.season_id,
  -- TM position takes priority; fall back to SofaScore if no TM match
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
  -- Transfermarkt financial/profile data
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
  tm.club_id                                                                 AS tm_club_id
FROM `real-zaragoza-500608.gold.fct_player_season_stats` s
LEFT JOIN `real-zaragoza-500608.gold.agg_player_market_values` tm
  ON LOWER(TRIM(s.player_name))  = LOWER(TRIM(tm.name))
 AND LOWER(TRIM(s.team_name))   = LOWER(TRIM(tm.club_name))
 AND CAST(s.season_id AS STRING) = CAST(tm.season_id AS STRING)
