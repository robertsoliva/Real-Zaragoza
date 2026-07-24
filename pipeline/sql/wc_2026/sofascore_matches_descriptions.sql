ALTER TABLE `real-zaragoza-500608.wc_2026.sofascore_matches`
  SET OPTIONS(description="GRAIN: one row per (match_id, scrape run) — NOT deduplicated. SOURCE: scraper_sofascore.py run with BQ_DATASET=wc_2026, TOURNAMENT_ID=16, SEASON_ID=58210. PARTITION BY match_date (DAY). CLUSTER BY match_round, tournament_id. NOTES: FIFA World Cup 2026 data only. Tournament ended ~2026-07-19 — no further writes expected. Merged into bronze.matches via UNION ALL with dataset_source='wc_26'. Identical schema to raw.sofascore_matches.");

ALTER TABLE `real-zaragoza-500608.wc_2026.sofascore_matches`
  ALTER COLUMN match_id SET OPTIONS(description="SofaScore unique match identifier (string)"),
  ALTER COLUMN match_date SET OPTIONS(description="Date the match was played (partition key)"),
  ALTER COLUMN match_round SET OPTIONS(description="Round number within the WC 2026 tournament"),
  ALTER COLUMN tournament_id SET OPTIONS(description="SofaScore tournament ID — always '16' for FIFA World Cup"),
  ALTER COLUMN season_id SET OPTIONS(description="SofaScore season ID — always '58210' for WC 2026"),
  ALTER COLUMN league_name SET OPTIONS(description="League/tournament name — 'FIFA World Cup' for all rows"),
  ALTER COLUMN home_team_id SET OPTIONS(description="SofaScore team ID for the home side (string)"),
  ALTER COLUMN home_team_name SET OPTIONS(description="Home team/nation name"),
  ALTER COLUMN away_team_id SET OPTIONS(description="SofaScore team ID for the away side (string)"),
  ALTER COLUMN away_team_name SET OPTIONS(description="Away team/nation name"),
  ALTER COLUMN home_score SET OPTIONS(description="Full-time home score"),
  ALTER COLUMN away_score SET OPTIONS(description="Full-time away score"),
  ALTER COLUMN status SET OPTIONS(description="Match status string (e.g. 'finished')"),
  ALTER COLUMN ingested_date SET OPTIONS(description="Calendar date when this row was written by the scraper"),
  ALTER COLUMN ingested_at SET OPTIONS(description="Full ISO timestamp when this row was written by the scraper")
