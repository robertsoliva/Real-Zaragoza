CREATE OR REPLACE VIEW `real-zaragoza-500608.bronze.rz_squad`
OPTIONS(description="Pass-through view of raw.transfermarkt_squad. Contains the latest Transfermarkt squad data for Real Zaragoza only (single-club scrape). Bronze layer — no deduplication applied here.")
AS
SELECT * FROM `real-zaragoza-500608.raw.transfermarkt_squad`
