CREATE OR REPLACE TABLE `real-zaragoza-500608.rz_gold.gold_zaragoza_matches`
PARTITION BY match_date
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
FROM `real-zaragoza-500608.rz_silver.silver_matches` m
LEFT JOIN `real-zaragoza-500608.rz_silver.silver_team_stats` ts
  ON m.match_id = ts.match_id AND ts.team_id = "2815"
WHERE m.home_team_id = "2815" OR m.away_team_id = "2815"
