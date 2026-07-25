{{ config(
    alias='tm_players',
    cluster_by=['league_name', 'season_id']
) }}

WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY player_id, club_id, season_id
      ORDER BY ingested_date DESC
    ) AS rn
  FROM {{ ref('bronze_tm_players') }}
  WHERE player_id IS NOT NULL
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
