{{ config(alias='bqml_wages') }}

-- Deduplicates to the latest prediction per player (by name), regardless of club.
-- Club-name join would fail for players who moved between TM scrape and their
-- historical season in the scouting table, so we match on name only.
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY LOWER(TRIM(player_name))
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
  raw_predicted_wage_eur_weekly,
  league_multiplier,
  predicted_wage_eur_weekly,
  predicted_wage_eur_annual,
  prediction_date
FROM ranked
WHERE rn = 1
