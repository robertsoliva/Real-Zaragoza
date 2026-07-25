{{ config(
    alias='shots',
    partition_by={
        'field': 'match_date',
        'data_type': 'date',
        'granularity': 'day'
    },
    cluster_by=['tournament_id']
) }}

WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY shot_id ORDER BY ingested_at DESC) AS rn
  FROM {{ ref('bronze_shots') }}
),
deduped AS (
  SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
)
SELECT
  s.shot_id, s.match_id, s.match_date, s.match_round,
  s.tournament_id, s.season_id, s.league_name, s.dataset_source,
  s.player_id, s.player_name,
  CASE WHEN s.is_home THEN m.home_team_id ELSE m.away_team_id END     AS team_id,
  CASE WHEN s.is_home THEN m.home_team_name ELSE m.away_team_name END  AS team_name,
  s.is_home, s.minute, s.added_time, s.time_seconds,
  s.x, s.y, s.goal_mouth_x, s.goal_mouth_y, s.goal_mouth_z, s.goal_mouth_location,
  s.block_x, s.block_y, s.body_part, s.shot_type, s.situation, s.xg
FROM deduped s
LEFT JOIN {{ ref('silver_matches') }} m USING (match_id)
