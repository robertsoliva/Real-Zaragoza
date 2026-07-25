{{ config(
    materialized='incremental',
    unique_key='player_id',
    incremental_strategy='merge',
    merge_update_columns=['player_id']
) }}

WITH player_base AS (
  SELECT
    player_id,
    ANY_VALUE(player_name)      AS player_name,
    ANY_VALUE(primary_position) AS primary_position
  FROM {{ ref('fct_player_season_stats') }}
  GROUP BY player_id
),
player_tm AS (
  SELECT
    sofascore_id,
    ANY_VALUE(tm_position)  AS tm_position,
    ANY_VALUE(nationality)  AS nationality,
    ANY_VALUE(foot)         AS foot,
    ANY_VALUE(height)       AS height
  FROM {{ ref('agg_scouting_player_season') }}
  WHERE sofascore_id IS NOT NULL
  GROUP BY sofascore_id
)
SELECT
  p.player_id,
  p.player_name,
  p.primary_position,
  t.tm_position,
  t.nationality,
  t.foot,
  t.height
FROM player_base p
LEFT JOIN player_tm t ON p.player_id = t.sofascore_id

{% if is_incremental() %}
  WHERE p.player_id NOT IN (SELECT player_id FROM {{ this }})
{% endif %}
