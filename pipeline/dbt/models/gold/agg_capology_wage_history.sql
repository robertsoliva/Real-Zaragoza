{{ config(cluster_by=['league_name', 'position_group']) }}

-- Mirrors agg_tm_player_valuations: reads raw directly (not silver, which
-- collapses to the latest snapshot per player+club+league) so every quarterly
-- Capology snapshot is preserved for wage-evolution-over-time analysis.
-- snapshot_rank=1 is the most recent. Same data-quality filters as
-- silver_capology_wages (loans excluded, non-positive wages excluded) --
-- those are correctness exclusions, not just latest-snapshot dedup, so they
-- apply here too.
--
-- SELECT DISTINCT below: raw.capology_wages has exact full-row duplicates
-- (~half the table, all ingested_date=2026-07-25) -- the scraper's
-- WRITE_APPEND has no run-level idempotency guard, so if the job ever ran
-- twice on the same day every row gets written twice. Collapsing exact
-- duplicates here is a workaround, not a fix -- the real fix is scraper-side
-- (see next-actions.md).

WITH deduped_raw AS (
  SELECT DISTINCT *
  FROM {{ source('raw', 'capology_wages') }}
  WHERE on_loan IS DISTINCT FROM TRUE
    AND wage_eur_weekly > 0
)
SELECT
  player_name,
  primary_position,
  position_group,
  age,
  club_name,
  nationality,
  league_name,
  league_tier,
  wage_eur_weekly,
  ROUND(wage_eur_weekly * 52, 0)                                              AS wage_eur_annual,
  active,
  ingested_date,
  ROW_NUMBER() OVER (
    PARTITION BY LOWER(TRIM(player_name)), LOWER(TRIM(club_name)), league_name
    ORDER BY ingested_date DESC
  )                                                                            AS snapshot_rank
FROM deduped_raw
