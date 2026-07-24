ALTER TABLE `real-zaragoza-500608.gold.agg_tm_player_valuations`
  ALTER COLUMN player_id SET OPTIONS(description="Transfermarkt internal player identifier (cluster column)"),
  ALTER COLUMN player_name SET OPTIONS(description="Player full name from Transfermarkt"),
  ALTER COLUMN club_id SET OPTIONS(description="Transfermarkt internal club identifier"),
  ALTER COLUMN club_name SET OPTIONS(description="Club name at time of scrape"),
  ALTER COLUMN league_name SET OPTIONS(description="League name at time of scrape (cluster column)"),
  ALTER COLUMN season_id SET OPTIONS(description="Season year string (e.g. 2024)"),
  ALTER COLUMN position SET OPTIONS(description="Transfermarkt position label at time of scrape"),
  ALTER COLUMN age SET OPTIONS(description="Player age at time of scrape"),
  ALTER COLUMN nationality SET OPTIONS(description="Primary nationality"),
  ALTER COLUMN market_value_eur SET OPTIONS(description="Transfermarkt estimated market value in EUR — tracks change across ingested_date values"),
  ALTER COLUMN contract_expiry SET OPTIONS(description="Contract expiry date at time of scrape"),
  ALTER COLUMN ingested_date SET OPTIONS(description="Date this snapshot was scraped — group by this column to observe value evolution over time"),
  ALTER COLUMN snapshot_rank SET OPTIONS(description="Rank within (player_id, club_id, season_id) ordered by ingested_date DESC — rank=1 is the most recent snapshot")
