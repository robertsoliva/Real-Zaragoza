CREATE OR REPLACE TABLE `real-zaragoza-500608.silver.tm_players`
OPTIONS(description="Deduplicated multi-league Transfermarkt player data. One row per (player_id, club_id, season_id), keeping the latest ingestion. Clustered by league_name and season_id for efficient scouting queries. Source: bronze.tm_players.")
CLUSTER BY league_name, season_id
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY player_id, club_id, season_id
      ORDER BY ingested_date DESC
    ) AS rn
  FROM `real-zaragoza-500608.bronze.tm_players`
  WHERE player_id IS NOT NULL
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
