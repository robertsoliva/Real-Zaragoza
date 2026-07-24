ALTER TABLE `real-zaragoza-500608.silver.capology_wages`
  ALTER COLUMN player_name SET OPTIONS(description="Player full name as shown on Capology"),
  ALTER COLUMN primary_position SET OPTIONS(description="Detailed position from Capology (e.g. Centre-Back, Attacking Midfield)"),
  ALTER COLUMN position_group SET OPTIONS(description="Broad position group: ATT, MID, DEF, or GK"),
  ALTER COLUMN age SET OPTIONS(description="Player age at time of scrape"),
  ALTER COLUMN club_name SET OPTIONS(description="Current club name"),
  ALTER COLUMN nationality SET OPTIONS(description="Player nationality as shown on Capology"),
  ALTER COLUMN league_name SET OPTIONS(description="League name (Premier League, La Liga, Bundesliga, Ligue 1, or Serie A)"),
  ALTER COLUMN league_tier SET OPTIONS(description="League tier: always 1 (all Capology leagues are top division)"),
  ALTER COLUMN wage_eur_weekly SET OPTIONS(description="Reported gross weekly wage in EUR"),
  ALTER COLUMN wage_eur_annual SET OPTIONS(description="Gross annual wage in EUR (weekly × 52)"),
  ALTER COLUMN active SET OPTIONS(description="Whether the player is currently active at the club"),
  ALTER COLUMN ingested_date SET OPTIONS(description="Date of the most recent scrape for this player/club/league combination")
