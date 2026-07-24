CREATE OR REPLACE VIEW `real-zaragoza-500608.bronze.rz_squad`
OPTIONS(description="GRAIN: one row per (player, ingestion run) — NOT deduplicated; same player appears on every scrape date. SOURCE: raw.transfermarkt_squad, written by scraper_transfermarkt.py (Zaragoza single-club scraper). NOTES: pass-through view, no filtering or deduplication applied here — use silver.rz_squad for deduplicated data. No partition. No cluster.")
AS
SELECT * FROM `real-zaragoza-500608.raw.transfermarkt_squad`
