{{ config(
    alias='tm_players',
    cluster_by=['league_name', 'season_id']
) }}

-- Some TM competition pages render an extra column between nationality and height,
-- shifting the scraper offsets by 1. When this happens, the height value ends up in
-- the `foot` column and `height` is NULL. Detect and correct the swap here.
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY player_id, club_id, season_id
      ORDER BY ingested_date DESC
    ) AS rn
  FROM {{ ref('bronze_tm_players') }}
  WHERE player_id IS NOT NULL
),
corrected AS (
  SELECT * EXCEPT (rn, height, foot),
    CASE
      WHEN height IS NOT NULL AND REGEXP_CONTAINS(height, r'^\d+,\d+m$') THEN height
      WHEN height IS NULL AND REGEXP_CONTAINS(COALESCE(foot, ''), r'^\d+,\d+m$') THEN foot
      ELSE height
    END AS height,
    CASE
      WHEN REGEXP_CONTAINS(COALESCE(foot, ''), r'^\d+,\d+m$') THEN NULL
      ELSE foot
    END AS foot
  FROM ranked
  WHERE rn = 1
)
SELECT * FROM corrected
