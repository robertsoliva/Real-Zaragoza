{{ config(cluster_by=['league_name', 'position_group']) }}

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
  FROM {{ ref('silver_capology_wages') }} c
  LEFT JOIN {{ ref('silver_tm_players') }} tm
    ON LOWER(TRIM(c.player_name)) = LOWER(TRIM(tm.name))
   AND LOWER(TRIM(c.club_name))   = LOWER(TRIM(tm.club_name))
),
benchmarks_pct AS (
  SELECT DISTINCT
    league_name,
    league_tier,
    position_group,
    ROUND(PERCENTILE_CONT(wage_eur_annual, 0.25) OVER (
      PARTITION BY league_name, position_group), 0)  AS p25_wage_annual,
    ROUND(PERCENTILE_CONT(wage_eur_annual, 0.50) OVER (
      PARTITION BY league_name, position_group), 0)  AS median_wage_annual,
    ROUND(PERCENTILE_CONT(wage_eur_annual, 0.75) OVER (
      PARTITION BY league_name, position_group), 0)  AS p75_wage_annual
  FROM wages
),
benchmarks_agg AS (
  SELECT
    league_name,
    league_tier,
    position_group,
    COUNT(*)                                                              AS player_count,
    ROUND(AVG(wage_eur_annual), 0)                                       AS avg_wage_annual,
    ROUND(AVG(market_value_eur), 0)                                      AS avg_market_value_eur,
    ROUND(SAFE_DIVIDE(AVG(wage_eur_annual), AVG(market_value_eur)) * 100, 2) AS avg_wage_to_value_pct
  FROM wages
  GROUP BY league_name, league_tier, position_group
)
SELECT
  a.league_name,
  a.league_tier,
  a.position_group,
  a.player_count,
  p.p25_wage_annual,
  p.median_wage_annual,
  p.p75_wage_annual,
  a.avg_wage_annual,
  a.avg_market_value_eur,
  a.avg_wage_to_value_pct
FROM benchmarks_agg a
JOIN benchmarks_pct p
  ON  a.league_name    = p.league_name
  AND a.league_tier    = p.league_tier
  AND a.position_group = p.position_group
