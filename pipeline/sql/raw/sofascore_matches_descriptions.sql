ALTER TABLE `real-zaragoza-500608.raw.sofascore_matches`
  SET OPTIONS(description="GRAIN: one row per (match_id, scrape run) — NOT deduplicated; a match rescraped twice appears twice. SOURCE: scraper_sofascore.py, written via insert_rows_json on every launchd slot. PARTITION BY match_date (DAY). CLUSTER BY match_round, tournament_id. Deduplicated version: silver.matches.");

ALTER TABLE `real-zaragoza-500608.raw.sofascore_matches`
  ALTER COLUMN match_id SET OPTIONS(description="SofaScore unique match identifier (string)"),
  ALTER COLUMN match_date SET OPTIONS(description="Date the match was played (partition key), in YYYY-MM-DD format"),
  ALTER COLUMN match_round SET OPTIONS(description="Round or gameweek number within the season"),
  ALTER COLUMN tournament_id SET OPTIONS(description="SofaScore tournament/competition identifier (e.g. '54' = LaLiga2)"),
  ALTER COLUMN season_id SET OPTIONS(description="SofaScore season identifier (e.g. '62048' = LaLiga2 2024-25)"),
  ALTER COLUMN league_name SET OPTIONS(description="Human-readable league name (e.g. 'LaLiga2', 'Serie B')"),
  ALTER COLUMN home_team_id SET OPTIONS(description="SofaScore team ID for the home team (string)"),
  ALTER COLUMN home_team_name SET OPTIONS(description="Home team name as returned by SofaScore"),
  ALTER COLUMN away_team_id SET OPTIONS(description="SofaScore team ID for the away team (string)"),
  ALTER COLUMN away_team_name SET OPTIONS(description="Away team name as returned by SofaScore"),
  ALTER COLUMN home_score SET OPTIONS(description="Full-time home team goals scored"),
  ALTER COLUMN away_score SET OPTIONS(description="Full-time away team goals scored"),
  ALTER COLUMN status SET OPTIONS(description="Match status string from SofaScore (e.g. 'finished', 'postponed')"),
  ALTER COLUMN ingested_date SET OPTIONS(description="Calendar date when this row was written by the scraper"),
  ALTER COLUMN ingested_at SET OPTIONS(description="Full ISO timestamp when this row was written by the scraper")
