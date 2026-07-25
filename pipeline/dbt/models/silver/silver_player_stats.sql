{{ config(
    alias='player_stats',
    partition_by={
        'field': 'match_date',
        'data_type': 'date',
        'granularity': 'day'
    },
    cluster_by=['tournament_id', 'team_id']
) }}

WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY match_id, player_id ORDER BY ingested_at DESC) AS rn
  FROM {{ ref('bronze_player_stats') }}
),
deduped AS (
  SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
)
SELECT
  d.match_id, d.player_id, d.match_date, d.match_round,
  d.tournament_id, d.season_id, d.league_name, d.dataset_source,
  d.player_name,
  CASE WHEN d.is_home THEN m.home_team_id ELSE m.away_team_id END     AS team_id,
  CASE WHEN d.is_home THEN m.home_team_name ELSE m.away_team_name END  AS team_name,
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
LEFT JOIN {{ ref('silver_matches') }} m USING (match_id)
