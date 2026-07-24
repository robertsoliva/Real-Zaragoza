CREATE OR REPLACE VIEW `real-zaragoza-500608.bronze.capology_wages`
OPTIONS(description="GRAIN: one row per (player, club, ingestion run) — NOT deduplicated. SOURCE: raw.capology_wages, written by scraper_capology.py (monthly Cloud Run Job rz-capology-scraper). NOTES: covers top 5 EU leagues only (PL, La Liga, Bundesliga, Ligue 1, Serie A — NOT the 2nd-division leagues in the SofaScore pipeline). Loan players included at this layer; excluded at silver. No partition. No cluster.")
AS
SELECT * FROM `real-zaragoza-500608.raw.capology_wages`
