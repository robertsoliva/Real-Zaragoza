ALTER TABLE `real-zaragoza-500608.gold.agg_player_wage_benchmarks`
  ALTER COLUMN league_name SET OPTIONS(description="League name (cluster column): Premier League, La Liga, Bundesliga, Ligue 1, or Serie A"),
  ALTER COLUMN league_tier SET OPTIONS(description="League tier: always 1 (Capology covers top divisions only)"),
  ALTER COLUMN position_group SET OPTIONS(description="Broad position group: ATT, MID, DEF, or GK (cluster column)"),
  ALTER COLUMN player_count SET OPTIONS(description="Number of players contributing to this league/position benchmark"),
  ALTER COLUMN p25_wage_annual SET OPTIONS(description="25th percentile gross annual wage in EUR for this league and position group"),
  ALTER COLUMN median_wage_annual SET OPTIONS(description="Median (50th percentile) gross annual wage in EUR"),
  ALTER COLUMN p75_wage_annual SET OPTIONS(description="75th percentile gross annual wage in EUR"),
  ALTER COLUMN avg_wage_annual SET OPTIONS(description="Average gross annual wage in EUR"),
  ALTER COLUMN avg_market_value_eur SET OPTIONS(description="Average Transfermarkt market value in EUR for matched players (NULL for unmatched)"),
  ALTER COLUMN avg_wage_to_value_pct SET OPTIONS(description="Average ratio of annual wage to market value, expressed as a percentage — indicates typical wage cost relative to player value")
