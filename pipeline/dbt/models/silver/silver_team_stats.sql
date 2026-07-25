{{ config(
    alias='team_stats',
    partition_by={
        'field': 'match_date',
        'data_type': 'date',
        'granularity': 'day'
    },
    cluster_by=['tournament_id', 'team_id']
) }}

WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY match_id, team_id ORDER BY ingested_at DESC) AS rn
  FROM {{ ref('bronze_team_stats') }}
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
