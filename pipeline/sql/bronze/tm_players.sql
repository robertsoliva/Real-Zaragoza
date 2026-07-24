CREATE OR REPLACE VIEW `real-zaragoza-500608.bronze.tm_players`
OPTIONS(description="GRAIN: one row per (player, club, ingestion run) — NOT deduplicated; same player-club pair appears on every quarterly scrape. SOURCE: raw.transfermarkt_players, written by scraper_transfermarkt_leagues.py. NOTES: covers 19 active pipeline leagues (1RFEF excluded — too many clubs to scrape efficiently). Loan players included; deduplication and filtering at silver layer. No partition. No cluster.")
AS
SELECT * FROM `real-zaragoza-500608.raw.transfermarkt_players`
