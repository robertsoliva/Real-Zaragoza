CREATE OR REPLACE TABLE `real-zaragoza-500608.silver.shots`
PARTITION BY match_date
CLUSTER BY tournament_id
OPTIONS(description="GRAIN: one row per shot_id — latest ingestion only. SOURCE: bronze.shots; JOINs silver.matches to resolve team_id/team_name from is_home flag. DEDUP: ROW_NUMBER() OVER (PARTITION BY shot_id ORDER BY ingested_at DESC). NOTES: pitch coordinates (x, y) use SofaScore's 0–100 coordinate system. xg is the expected-goals value for this specific shot. goal_mouth_location is a string label (e.g. 'HighCentre'). PARTITION BY match_date (DAY). CLUSTER BY tournament_id.")
AS
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY shot_id ORDER BY ingested_at DESC) AS rn
  FROM `real-zaragoza-500608.bronze.shots`
),
deduped AS (
  SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
)
SELECT
  s.shot_id, s.match_id, s.match_date, s.match_round,
  s.tournament_id, s.season_id, s.league_name, s.dataset_source,
  s.player_id, s.player_name,
  CASE WHEN s.is_home THEN m.home_team_id ELSE m.away_team_id END AS team_id,
  CASE WHEN s.is_home THEN m.home_team_name ELSE m.away_team_name END AS team_name,
  s.is_home, s.minute, s.added_time, s.time_seconds,
  s.x, s.y, s.goal_mouth_x, s.goal_mouth_y, s.goal_mouth_z, s.goal_mouth_location,
  s.block_x, s.block_y, s.body_part, s.shot_type, s.situation, s.xg
FROM deduped s
LEFT JOIN `real-zaragoza-500608.silver.matches` m USING (match_id)
