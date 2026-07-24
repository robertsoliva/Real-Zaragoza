ALTER TABLE `real-zaragoza-500608.raw.transfermarkt_squad`
  SET OPTIONS(description="GRAIN: one row per (player, ingestion run) — NOT deduplicated; same player appears on every scrape. SOURCE: scraper_transfermarkt.py (Real Zaragoza single-club TM scraper). PARTITION BY ingested_date (DAY). CLUSTER BY season_id, player_id. NOTES: Zaragoza-only table — for multi-league TM data use raw.transfermarkt_players. Deduplicated version: silver.rz_squad. Financial overview: gold.agg_rz_squad_finances.");

ALTER TABLE `real-zaragoza-500608.raw.transfermarkt_squad`
  ALTER COLUMN ingested_date SET OPTIONS(description="Calendar date of the scrape run (partition key)"),
  ALTER COLUMN season_id SET OPTIONS(description="TM season year string (e.g. '2025' for 2025-26 season)"),
  ALTER COLUMN player_id SET OPTIONS(description="Transfermarkt player ID extracted from profile URL"),
  ALTER COLUMN name SET OPTIONS(description="Player full name as shown on Transfermarkt"),
  ALTER COLUMN date_of_birth SET OPTIONS(description="Player date of birth (ISO date string)"),
  ALTER COLUMN jersey_number SET OPTIONS(description="Squad jersey number"),
  ALTER COLUMN position SET OPTIONS(description="Granular TM position (e.g. 'Centre-Back', 'Left Winger')"),
  ALTER COLUMN age SET OPTIONS(description="Player age at time of scrape"),
  ALTER COLUMN nationality SET OPTIONS(description="Primary nationality"),
  ALTER COLUMN height SET OPTIONS(description="Player height in centimetres"),
  ALTER COLUMN foot SET OPTIONS(description="Preferred foot ('left', 'right', 'both')"),
  ALTER COLUMN joined_date SET OPTIONS(description="Date the player joined Zaragoza"),
  ALTER COLUMN signed_from SET OPTIONS(description="Club or free agent the player was signed from"),
  ALTER COLUMN signing_fee SET OPTIONS(description="Reported transfer fee paid when joining Zaragoza"),
  ALTER COLUMN contract_expiry SET OPTIONS(description="Contract expiry date at Zaragoza"),
  ALTER COLUMN market_value_eur SET OPTIONS(description="Transfermarkt estimated market value in EUR at time of scrape"),
  ALTER COLUMN ingested_at SET OPTIONS(description="Full ISO timestamp when this row was written by the scraper")
