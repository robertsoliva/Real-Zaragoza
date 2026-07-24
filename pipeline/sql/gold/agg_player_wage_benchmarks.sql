-- Wage benchmarks by position group and league.
-- Joins Capology wage data with TM market values for each player,
-- giving a combined view useful for scouting budget planning:
-- what does a player of this value/age/position typically earn?
CREATE OR REPLACE TABLE `real-zaragoza-500608.gold.agg_player_wage_benchmarks`
OPTIONS(description="Wage benchmarks by position group and league. Aggregates Capology gross wage data joined with TM market values. Provides P25/median/P75/avg annual wage and avg_wage_to_value_pct per (league, position group). Use for scouting budget planning and wage-to-value ratio analysis. Clustered by league_name and position_group.")
CLUSTER BY league_name, position_group
AS
WITH wages AS (
  SELECT
    c.player_name,
    c.primary_position,
    c.position_group,
    c.age,
    c.club_name,
    c.nationality,
    c.league_name,
    c.league_tier,
    c.wage_eur_weekly,
    c.wage_eur_annual,
    c.ingested_date,
    tm.market_value_eur,
    tm.contract_expiry,
    tm.foot,
    tm.height
  FROM `real-zaragoza-500608.silver.capology_wages` c
  LEFT JOIN `real-zaragoza-500608.silver.tm_players` tm
    ON LOWER(TRIM(c.player_name)) = LOWER(TRIM(tm.name))
   AND LOWER(TRIM(c.club_name))   = LOWER(TRIM(tm.club_name))
),
benchmarks AS (
  SELECT
    league_name,
    league_tier,
    position_group,
    COUNT(*)                                                              AS player_count,
    ROUND(PERCENTILE_CONT(wage_eur_annual, 0.25) OVER (
      PARTITION BY league_name, position_group), 0)                      AS p25_wage_annual,
    ROUND(PERCENTILE_CONT(wage_eur_annual, 0.50) OVER (
      PARTITION BY league_name, position_group), 0)                      AS median_wage_annual,
    ROUND(PERCENTILE_CONT(wage_eur_annual, 0.75) OVER (
      PARTITION BY league_name, position_group), 0)                      AS p75_wage_annual,
    ROUND(AVG(wage_eur_annual), 0)                                       AS avg_wage_annual,
    ROUND(AVG(market_value_eur), 0)                                      AS avg_market_value_eur,
    ROUND(SAFE_DIVIDE(AVG(wage_eur_annual), AVG(market_value_eur)) * 100, 2)
                                                                          AS avg_wage_to_value_pct
  FROM wages
  GROUP BY league_name, league_tier, position_group
)
SELECT DISTINCT
  b.league_name,
  b.league_tier,
  b.position_group,
  b.player_count,
  b.p25_wage_annual,
  b.median_wage_annual,
  b.p75_wage_annual,
  b.avg_wage_annual,
  b.avg_market_value_eur,
  b.avg_wage_to_value_pct
FROM benchmarks b
ORDER BY b.league_tier, b.league_name, b.position_group
