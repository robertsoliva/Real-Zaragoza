{{ config(alias='rz_squad') }}

WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY ingested_date DESC) AS rn
  FROM {{ ref('bronze_rz_squad') }}
)
SELECT * EXCEPT (rn) FROM ranked WHERE rn = 1
