{{ config(
    materialized='incremental',
    unique_key='tournament_id',
    incremental_strategy='merge',
    merge_update_columns=['tournament_id']
) }}

WITH leagues AS (
  SELECT DISTINCT
    tournament_id,
    league_name,
    dataset_source,
    CASE tournament_id
      WHEN '8'     THEN 'Spain'
      WHEN '16'    THEN 'World'
      WHEN '17'    THEN 'England'
      WHEN '20'    THEN 'Norway'
      WHEN '23'    THEN 'Italy'
      WHEN '34'    THEN 'France'
      WHEN '35'    THEN 'Germany'
      WHEN '37'    THEN 'Netherlands'
      WHEN '38'    THEN 'Belgium'
      WHEN '40'    THEN 'Sweden'
      WHEN '44'    THEN 'Germany'
      WHEN '45'    THEN 'Austria'
      WHEN '52'    THEN 'Turkey'
      WHEN '53'    THEN 'Italy'
      WHEN '54'    THEN 'Spain'
      WHEN '131'   THEN 'Netherlands'
      WHEN '152'   THEN 'Romania'
      WHEN '182'   THEN 'France'
      WHEN '196'   THEN 'Japan'
      WHEN '210'   THEN 'Serbia'
      WHEN '238'   THEN 'Portugal'
      WHEN '242'   THEN 'United States'
      WHEN '390'   THEN 'Brazil'
      WHEN '410'   THEN 'South Korea'
      WHEN '685'   THEN 'Moldova'
      WHEN '17073' THEN 'Spain'
      ELSE NULL
    END AS country
  FROM {{ ref('silver_matches') }}
)
SELECT * FROM leagues

{% if is_incremental() %}
  WHERE tournament_id NOT IN (SELECT tournament_id FROM {{ this }})
{% endif %}
