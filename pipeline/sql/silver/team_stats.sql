CREATE OR REPLACE TABLE `real-zaragoza-500608.silver.team_stats`
OPTIONS(description="GRAIN: one row per (match_id, team_id) — latest ingestion only; two rows per match (one per side). SOURCE: bronze.team_stats (UNION ALL of raw + wc_2026). DEDUP: ROW_NUMBER() OVER (PARTITION BY match_id, team_id ORDER BY ingested_at DESC). NOTES: includes full match stats — shots, passes, corners, fouls, aerial/ground duels, big chances, final-third entries. Used by gold.fct_rz_matches to pull Zaragoza's per-match stats. PARTITION BY match_date (DAY). CLUSTER BY tournament_id, team_id.")
PARTITION BY match_date
CLUSTER BY tournament_id, team_id
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY match_id, team_id ORDER BY ingested_at DESC) AS rn
  FROM `real-zaragoza-500608.bronze.team_stats`
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
