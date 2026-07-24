CREATE OR REPLACE VIEW `real-zaragoza-500608.bronze.tm_players`
OPTIONS(description="Pass-through view of raw.transfermarkt_players. Contains Transfermarkt squad and market value data for all active pipeline leagues (1RFEF excluded). Bronze layer — no deduplication applied here.")
AS
SELECT * FROM `real-zaragoza-500608.raw.transfermarkt_players`
