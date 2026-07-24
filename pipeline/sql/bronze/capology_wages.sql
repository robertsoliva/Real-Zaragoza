CREATE OR REPLACE VIEW `real-zaragoza-500608.bronze.capology_wages`
OPTIONS(description="Pass-through view of raw.capology_wages. Contains reported gross wage data scraped from Capology for the top 5 EU leagues (Premier League, La Liga, Bundesliga, Ligue 1, Serie A). Bronze layer — no deduplication applied here.")
AS
SELECT * FROM `real-zaragoza-500608.raw.capology_wages`
