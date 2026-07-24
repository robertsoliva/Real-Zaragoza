-- Deduplicates to the latest ingestion per (player, club, league).
-- Excludes players on loan (their wage inflates the parent club's number).
CREATE OR REPLACE TABLE `real-zaragoza-500608.silver.capology_wages`
CLUSTER BY league_name, position_group
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY LOWER(TRIM(player_name)), LOWER(TRIM(club_name)), league_name
      ORDER BY ingested_date DESC
    ) AS rn
  FROM `real-zaragoza-500608.bronze.capology_wages`
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
  ROUND(wage_eur_weekly * 52, 0)  AS wage_eur_annual,
  active,
  ingested_date
FROM ranked
WHERE rn = 1
