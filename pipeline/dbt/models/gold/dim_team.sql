{{ config(
    materialized='incremental',
    unique_key='team_id',
    incremental_strategy='merge',
    merge_update_columns=['team_id']
) }}

WITH all_teams AS (
  SELECT DISTINCT home_team_id AS team_id, home_team_name AS team_name
  FROM {{ ref('silver_matches') }}
  UNION DISTINCT
  SELECT DISTINCT away_team_id AS team_id, away_team_name AS team_name
  FROM {{ ref('silver_matches') }}
)
SELECT team_id, team_name
FROM all_teams
WHERE team_id IS NOT NULL

{% if is_incremental() %}
  AND team_id NOT IN (SELECT team_id FROM {{ this }})
{% endif %}
