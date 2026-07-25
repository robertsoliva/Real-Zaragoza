{{ config(
    alias='capology_wages',
    cluster_by=['league_name', 'position_group']
) }}

WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY LOWER(TRIM(player_name)), LOWER(TRIM(club_name)), league_name
      ORDER BY ingested_date DESC
    ) AS rn
  FROM {{ ref('bronze_capology_wages') }}
  WHERE on_loan IS DISTINCT FROM TRUE
    AND wage_eur_weekly > 0
)
SELECT
  player_name,
  primary_position,
  position_group,
  age,
  club_name,
  nationality,
  league_name,
  league_tier,
  wage_eur_weekly,
  ROUND(wage_eur_weekly * 52, 0) AS wage_eur_annual,
  active,
  ingested_date
FROM ranked
WHERE rn = 1
