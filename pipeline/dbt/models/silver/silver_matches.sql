{{ config(
    alias='matches',
    partition_by={
        'field': 'match_date',
        'data_type': 'date',
        'granularity': 'day'
    },
    cluster_by=['tournament_id', 'match_round']
) }}

WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY ingested_at DESC) AS rn
  FROM {{ ref('bronze_matches') }}
)
SELECT
  match_id, match_date, match_round, tournament_id, season_id, league_name, dataset_source,
  home_team_id, home_team_name, away_team_id, away_team_name,
  home_score, away_score, status
FROM ranked WHERE rn = 1
