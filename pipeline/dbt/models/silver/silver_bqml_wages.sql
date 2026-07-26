{{ config(alias='bqml_wages') }}

WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY LOWER(TRIM(player_name)), LOWER(TRIM(club_name))
      ORDER BY prediction_date DESC
    ) AS rn
  FROM {{ source('raw', 'bqml_wage_predictions') }}
)
SELECT
  player_name,
  club_name,
  league_name,
  tm_position,
  market_value_eur,
  predicted_wage_eur_weekly,
  predicted_wage_eur_annual,
  prediction_date
FROM ranked
WHERE rn = 1
