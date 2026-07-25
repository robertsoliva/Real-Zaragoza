CREATE OR REPLACE TABLE `real-zaragoza-500608.gold.fct_rz_matches`
PARTITION BY match_date
CLUSTER BY season_id, result
OPTIONS(description="GRAIN: one row per match where Real Zaragoza (SofaScore team_id='2815') played. SOURCE: silver.matches (match metadata) LEFT JOIN silver.team_stats (Zaragoza's match stats). NOTES: result (W/D/L), venue (home/away), rz_goals, opponent_goals, and opponent derived in SQL. team_stats columns (possession_pct, total_shots, etc.) are Zaragoza's own stats only — NULL if stats not scraped for that match. Covers all seasons with Zaragoza data in the pipeline (LaLiga2 and 1RFEF). PARTITION BY match_date (DAY). CLUSTER BY season_id, result.")
AS
SELECT
  m.match_id, m.match_date, m.match_round, m.league_name, m.season_id,
  m.home_team_name, m.away_team_name, m.home_score, m.away_score,
  CASE
    WHEN m.home_team_id = "2815" AND m.home_score > m.away_score THEN "W"
    WHEN m.away_team_id = "2815" AND m.away_score > m.home_score THEN "W"
    WHEN m.home_score = m.away_score THEN "D"
    ELSE "L"
  END AS result,
  CASE WHEN m.home_team_id = "2815" THEN "home" ELSE "away" END AS venue,
  CASE WHEN m.home_team_id = "2815" THEN m.home_score ELSE m.away_score END AS rz_goals,
  CASE WHEN m.home_team_id = "2815" THEN m.away_score ELSE m.home_score END AS opponent_goals,
  CASE WHEN m.home_team_id = "2815" THEN m.away_team_name ELSE m.home_team_name END AS opponent,
  ts.possession_pct, ts.total_shots, ts.shots_on_target,
  ts.total_passes, ts.accurate_passes, ts.total_tackles, ts.interceptions, ts.fouls,
  ts.big_chances, ts.corners
FROM `real-zaragoza-500608.silver.matches` m
LEFT JOIN `real-zaragoza-500608.silver.team_stats` ts
  ON m.match_id = ts.match_id AND ts.team_id = "2815"
WHERE m.home_team_id = "2815" OR m.away_team_id = "2815"
