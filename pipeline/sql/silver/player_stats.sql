CREATE OR REPLACE TABLE `real-zaragoza-500608.silver.player_stats`
OPTIONS(description="GRAIN: one row per (match_id, player_id) — latest ingestion only. SOURCE: bronze.player_stats; JOINs silver.matches to resolve team_id/team_name from is_home flag. DEDUP: ROW_NUMBER() OVER (PARTITION BY match_id, player_id ORDER BY ingested_at DESC). NOTES: team_id and team_name derived from match home/away side, not from player row directly. minutes_played > 0 filter NOT applied here — applied at gold.fct_player_season_stats. PARTITION BY match_date (DAY). CLUSTER BY tournament_id, team_id.")
PARTITION BY match_date
CLUSTER BY tournament_id, team_id
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY match_id, player_id ORDER BY ingested_at DESC) AS rn
  FROM `real-zaragoza-500608.bronze.player_stats`
),
deduped AS (
  SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
)
SELECT
  d.match_id, d.player_id, d.match_date, d.match_round,
  d.tournament_id, d.season_id, d.league_name, d.dataset_source,
  d.player_name,
  CASE WHEN d.is_home THEN m.home_team_id ELSE m.away_team_id END AS team_id,
  CASE WHEN d.is_home THEN m.home_team_name ELSE m.away_team_name END AS team_name,
  d.is_home, d.position, d.shirt_number, d.is_substitute, d.captain,
  d.minutes_played, d.goals, d.goal_assists, d.rating,
  d.total_passes, d.accurate_passes, d.total_long_balls, d.accurate_long_balls,
  d.total_crosses, d.accurate_crosses, d.key_passes,
  d.total_shots, d.shots_on_target,
  d.aerial_won, d.aerial_lost, d.duel_won, d.duel_lost, d.challenge_lost,
  d.total_tackle, d.won_tackle, d.interceptions, d.total_clearance,
  d.ball_recovery, d.dispossessed, d.was_fouled, d.fouls,
  d.touches, d.possession_lost, d.unsuccessful_touch,
  d.yellow_cards, d.red_cards, d.saves, d.expected_goals, d.expected_assists
FROM deduped d
LEFT JOIN `real-zaragoza-500608.silver.matches` m USING (match_id)
