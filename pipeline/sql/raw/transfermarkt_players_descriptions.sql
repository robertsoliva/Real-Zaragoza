ALTER TABLE `real-zaragoza-500608.raw.transfermarkt_players`
  SET OPTIONS(description="GRAIN: one row per (player, club, ingestion run) — NOT deduplicated; same player-club pair appears on each quarterly scrape. SOURCE: scraper_transfermarkt_leagues.py (Cloud Run Job rz-tm-scraper, quarterly 1 Jan/Apr/Jul/Oct). PARTITION BY ingested_date (DAY). CLUSTER BY tm_league_code, season_id. NOTES: covers 19 active pipeline leagues (1RFEF excluded). market_value_eur and contract_expiry may be NULL for lower-profile players. Deduplicated version: silver.tm_players. Historical snapshots: gold.agg_tm_player_valuations.");

ALTER TABLE `real-zaragoza-500608.raw.transfermarkt_players`
  ALTER COLUMN player_id SET OPTIONS(description="Transfermarkt player ID extracted from profile URL"),
  ALTER COLUMN name SET OPTIONS(description="Player full name as shown on Transfermarkt"),
  ALTER COLUMN date_of_birth SET OPTIONS(description="Player date of birth (ISO date string)"),
  ALTER COLUMN jersey_number SET OPTIONS(description="Squad jersey number at this club"),
  ALTER COLUMN position SET OPTIONS(description="Granular TM position (e.g. 'Centre-Back', 'Left Winger', 'Central Midfield') — more detailed than SofaScore codes"),
  ALTER COLUMN age SET OPTIONS(description="Player age at time of scrape"),
  ALTER COLUMN nationality SET OPTIONS(description="Primary nationality"),
  ALTER COLUMN nationality_all SET OPTIONS(description="All nationalities (comma-separated if dual/triple)"),
  ALTER COLUMN height SET OPTIONS(description="Player height in centimetres (integer)"),
  ALTER COLUMN foot SET OPTIONS(description="Preferred foot ('left', 'right', 'both')"),
  ALTER COLUMN joined_date SET OPTIONS(description="Date the player joined this club"),
  ALTER COLUMN signed_from SET OPTIONS(description="Club or free agent the player was signed from"),
  ALTER COLUMN signing_fee SET OPTIONS(description="Reported transfer fee paid (string, e.g. '€5.00m')"),
  ALTER COLUMN contract_expiry SET OPTIONS(description="Contract expiry date at this club (ISO date string)"),
  ALTER COLUMN market_value_eur SET OPTIONS(description="Transfermarkt estimated market value in EUR at time of scrape (NULL if not listed)"),
  ALTER COLUMN ingested_at SET OPTIONS(description="Full ISO timestamp when this row was written by the scraper"),
  ALTER COLUMN club_id SET OPTIONS(description="Transfermarkt club ID extracted from club URL"),
  ALTER COLUMN club_slug SET OPTIONS(description="Transfermarkt club URL slug (e.g. 'real-zaragoza')"),
  ALTER COLUMN club_name SET OPTIONS(description="Club name as shown on Transfermarkt"),
  ALTER COLUMN tm_league_code SET OPTIONS(description="Transfermarkt competition code (e.g. 'ES2' = LaLiga2, 'IT2' = Serie B)"),
  ALTER COLUMN league_name SET OPTIONS(description="Human-readable league name corresponding to tm_league_code"),
  ALTER COLUMN ingested_date SET OPTIONS(description="Calendar date of the scrape run (partition key)")
