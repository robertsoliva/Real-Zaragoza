{{ config(alias='matches') }}

SELECT
  match_id, match_date, match_round, tournament_id, season_id,
  CASE WHEN tournament_id = '16' AND league_name = 'tournament_16' THEN 'FIFA World Cup'
       WHEN tournament_id = '35' THEN 'Bundesliga'
       WHEN tournament_id = '44' THEN '2. Bundesliga'
       WHEN tournament_id = '17' THEN 'Premier League'
       WHEN tournament_id = '8'  THEN 'La Liga'
       WHEN tournament_id = '23' THEN 'Serie A'
       WHEN tournament_id = '34' THEN 'Ligue 1'
       WHEN tournament_id = '239' AND league_name = 'tournament_239' THEN 'Liga Portugal 2'
       ELSE league_name END AS league_name,
  home_team_id, home_team_name, away_team_id, away_team_name,
  home_score, away_score, status, ingested_date, ingested_at,
  'standard' AS dataset_source
FROM {{ source('raw', 'sofascore_matches') }}

UNION ALL

SELECT
  match_id, match_date, match_round, tournament_id, season_id,
  CASE WHEN tournament_id = '16' AND league_name = 'tournament_16' THEN 'FIFA World Cup'
       WHEN tournament_id = '35' THEN 'Bundesliga'
       WHEN tournament_id = '44' THEN '2. Bundesliga'
       WHEN tournament_id = '17' THEN 'Premier League'
       WHEN tournament_id = '8'  THEN 'La Liga'
       WHEN tournament_id = '23' THEN 'Serie A'
       WHEN tournament_id = '34' THEN 'Ligue 1'
       WHEN tournament_id = '239' AND league_name = 'tournament_239' THEN 'Liga Portugal 2'
       ELSE league_name END AS league_name,
  home_team_id, home_team_name, away_team_id, away_team_name,
  home_score, away_score, status, ingested_date, ingested_at,
  'wc_26' AS dataset_source
FROM {{ source('wc_2026', 'sofascore_matches') }}
