ALTER TABLE `real-zaragoza-500608.bronze.capology_wages`
  ALTER COLUMN player_name SET OPTIONS(description="Player full name as shown on Capology"),
  ALTER COLUMN primary_position SET OPTIONS(description="Detailed position from Capology (e.g. Centre-Back, Attacking Midfield)"),
  ALTER COLUMN position_group SET OPTIONS(description="Broad position group: ATT, MID, DEF, or GK"),
  ALTER COLUMN age SET OPTIONS(description="Player age at time of scrape"),
  ALTER COLUMN club_name SET OPTIONS(description="Current club name"),
  ALTER COLUMN nationality SET OPTIONS(description="Player nationality or country code as shown on Capology"),
  ALTER COLUMN league_name SET OPTIONS(description="League name (Premier League, La Liga, Bundesliga, Ligue 1, or Serie A)"),
  ALTER COLUMN league_tier SET OPTIONS(description="League tier: always 1 (all Capology leagues are top division)"),
  ALTER COLUMN wage_eur_weekly SET OPTIONS(description="Reported gross weekly wage in EUR (annual / 52)"),
  ALTER COLUMN active SET OPTIONS(description="Whether the player is currently active at the club"),
  ALTER COLUMN on_loan SET OPTIONS(description="True if the player is on loan at this club — these rows are excluded in silver"),
  ALTER COLUMN ingested_date SET OPTIONS(description="Date the data was scraped from Capology")
