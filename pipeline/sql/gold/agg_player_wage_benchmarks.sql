-- Wage benchmarks by position group and league.
-- Joins Capology wage data with TM market values for each player,
-- giving a combined view useful for scouting budget planning:
-- what does a player of this value/age/position typically earn?
CREATE OR REPLACE TABLE `real-zaragoza-500608.gold.agg_player_wage_benchmarks`
CLUSTER BY league_name, position_group
OPTIONS(description="GRAIN: one row per (league_name, position_group) — wage distribution benchmarks across all qualifying players. SOURCE: silver.capology_wages LEFT JOIN silver.tm_players (matched on normalized name+club). NOTES: covers top 5 EU leagues ONLY (PL, La Liga, Bundesliga, Ligue 1, Serie A) — does NOT cover the 2nd-division or non-European leagues in the SofaScore pipeline. position_group uses broad codes (ATT/MID/DEF/GK). avg_wage_to_value_pct = (avg_annual_wage / avg_market_value) × 100. Use for profiling expected salary range for a player of given position/league when scouting from top leagues. CLUSTER BY league_name, position_group.")
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
