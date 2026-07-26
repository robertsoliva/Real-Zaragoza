#!/usr/bin/env python3
"""
rz-wage-predictor — BQML wage prediction pipeline.

Steps per run:
  1. Train/refresh ml.wage_regression on Capology × TM joined data.
  2. Evaluate the model and log R².
  3. Predict wages for every player in silver.tm_players with a known market value.
     Applies a per-league multiplier to correct for top-5-EU-only training bias.
  4. Append predictions to raw.bqml_wage_predictions.

Cadence: quarterly (Jan 2 / Apr 2 / Jul 2 / Oct 2) — 1 day after TM scrape so
the model always trains on the freshest market values.

League multipliers represent the ratio of average wages relative to the top-5 EU
baseline at equivalent market value. Derived from KPMG, CIES, and press reports.
Top-5 EU leagues use 1.0 (model trained directly on their data).
"""

import os
import logging
import sys
from google.cloud import bigquery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

PROJECT = os.environ.get("GCP_PROJECT_ID", "real-zaragoza-500608")
LOCATION = "europe-west1"

client = bigquery.Client(project=PROJECT, location=LOCATION)

# Multipliers relative to top-5 EU average wage for an equivalent market value.
# Top-5 EU = 1.0 (model trained on this data, no adjustment).
# Sources: KPMG Football Benchmark, CIES Football Observatory, football salary press.
# Multipliers calibrated as: target_avg_annual / raw_model_avg_annual
# where raw_model_avg_annual is the per-league average of EXP(predicted_log_wage)*52.
# Target salaries from KPMG Football Benchmark, CIES Observatory, SportPro (2025).
# Top-5 EU = 1.0 (model trained directly on their data; raw ≈ reality).
LEAGUE_MULTIPLIER_SQL = """
  CASE league_name
    WHEN 'Premier League'        THEN 1.00
    WHEN 'La Liga'               THEN 1.00
    WHEN 'Bundesliga'            THEN 1.00
    WHEN 'Serie A'               THEN 1.00
    WHEN 'Ligue 1'               THEN 1.00
    -- raw €729k → target €600k
    WHEN '2. Bundesliga'         THEN 0.82
    -- raw €1010k → target €700k (Galatasaray/Fenerbahce inflate average)
    WHEN 'Turkish Süper Lig'     THEN 0.69
    -- raw €471k → target €300k (J1 pays well relative to market values)
    WHEN 'J1 League'             THEN 0.64
    -- raw €871k → target €400k (DP rule skews MLS mean up)
    WHEN 'MLS'                   THEN 0.46
    -- raw €663k → target €300k
    WHEN 'Serie B'               THEN 0.45
    -- raw €676k → target €300k
    WHEN 'LaLiga2'               THEN 0.44
    -- raw €1026k → target €400k
    WHEN 'Eredivisie'            THEN 0.39
    -- raw €391k → target €150k
    WHEN 'Korean K League 1'     THEN 0.38
    -- raw €681k → target €250k
    WHEN 'Austrian Bundesliga'   THEN 0.37
    -- raw €997k → target €350k
    WHEN 'Belgian Pro League'    THEN 0.35
    -- raw €564k → target €200k
    WHEN 'Allsvenskan'           THEN 0.35
    -- raw €642k → target €200k
    WHEN 'Norwegian Eliteserien' THEN 0.31
    -- raw €655k → target €200k
    WHEN 'Ligue 2'               THEN 0.31
    -- raw €484k → target €150k
    WHEN 'Romanian SuperLiga'    THEN 0.31
    -- raw €388k → target €100k
    WHEN 'Eerste Divisie'        THEN 0.26
    -- raw €503k → target €120k
    WHEN 'Brasileirao Serie B'   THEN 0.24
    -- raw €325k → target €75k
    WHEN '1RFEF'                 THEN 0.23
    -- raw €1162k → target €250k (skewed by Benfica/Porto/Sporting squad values)
    WHEN 'Liga Portugal'         THEN 0.22
    -- raw €544k → target €100k
    WHEN 'Mozzart Bet Superliga' THEN 0.18
    -- raw €266k → target €30k
    WHEN 'Moldovan Super Liga'   THEN 0.11
    -- World Cup players are elite; treat as top-tier
    WHEN 'FIFA World Cup'        THEN 1.00
    ELSE 0.30
  END
"""

# ── 1. Train model ────────────────────────────────────────────────────────────
# Training set: Capology wages (top-5 EU, actual gross) joined with TM market
# values on normalised player+club name. ~1,500–2,000 rows after name-match drop-off.
# Features: log(market_value_eur), position_group (GK/DEF/MID/FWD).
# Label: log(wage_eur_weekly) — log-linear gives better fit across salary ranges.

SQL_TRAIN = f"""
CREATE OR REPLACE MODEL `{PROJECT}.ml.wage_regression`
OPTIONS (
  model_type        = 'linear_reg',
  input_label_cols  = ['log_wage_weekly'],
  data_split_method = 'AUTO_SPLIT',
  max_iterations    = 50
) AS
SELECT DISTINCT
  LOG(c.wage_eur_weekly)  AS log_wage_weekly,
  LOG(t.market_value_eur) AS log_market_value,
  c.position_group
FROM `{PROJECT}.silver.capology_wages` c
JOIN (
  SELECT name, club_name, market_value_eur, ingested_date,
         ROW_NUMBER() OVER (
           PARTITION BY LOWER(TRIM(name)), LOWER(TRIM(club_name))
           ORDER BY ingested_date DESC
         ) AS rn
  FROM `{PROJECT}.silver.tm_players`
  WHERE market_value_eur > 0
    AND player_id IS NOT NULL
) t ON t.rn = 1
   AND LOWER(TRIM(c.player_name)) = LOWER(TRIM(t.name))
   AND LOWER(TRIM(c.club_name))   = LOWER(TRIM(t.club_name))
WHERE c.wage_eur_weekly  > 0
  AND t.market_value_eur > 0
  AND c.position_group IS NOT NULL
"""

# ── 2. Evaluate ───────────────────────────────────────────────────────────────

SQL_EVALUATE = f"""
SELECT * FROM ML.EVALUATE(MODEL `{PROJECT}.ml.wage_regression`)
"""

# ── 3. Predict and append ─────────────────────────────────────────────────────
# Uses the latest row per player_id in silver.tm_players (most recent market value).
# ML.PREDICT passes through all non-feature columns unchanged.
# raw_predicted_wage_eur_weekly = raw model output (top-5 EU equivalent wage).
# predicted_wage_eur_weekly     = raw × league_multiplier (adjusted for league tier).

SQL_PREDICT = f"""
INSERT INTO `{PROJECT}.raw.bqml_wage_predictions`
  (player_name, club_name, league_name, tm_position, market_value_eur,
   raw_predicted_wage_eur_weekly, league_multiplier,
   predicted_wage_eur_weekly, predicted_wage_eur_annual, prediction_date)
WITH preds AS (
  SELECT
    name, club_name, league_name, position, market_value_eur,
    EXP(predicted_log_wage_weekly)                AS raw_wage,
    {LEAGUE_MULTIPLIER_SQL}                       AS multiplier
  FROM ML.PREDICT(
    MODEL `{PROJECT}.ml.wage_regression`,
    (
      SELECT
        name, club_name, league_name, position,
        market_value_eur,
        LOG(market_value_eur) AS log_market_value,
        CASE
          WHEN position = 'Goalkeeper'
            THEN 'GK'
          WHEN position IN ('Centre-Back', 'Left-Back', 'Right-Back')
            THEN 'DEF'
          WHEN position IN ('Defensive Midfield', 'Central Midfield',
                            'Attacking Midfield', 'Left Midfield', 'Right Midfield')
            THEN 'MID'
          WHEN position IN ('Left Winger', 'Right Winger',
                            'Centre-Forward', 'Second Striker')
            THEN 'FWD'
          ELSE 'MID'
        END AS position_group
      FROM (
        SELECT *,
          ROW_NUMBER() OVER (
            PARTITION BY player_id
            ORDER BY ingested_date DESC, season_id DESC
          ) AS rn
        FROM `{PROJECT}.silver.tm_players`
        WHERE market_value_eur > 0
          AND player_id IS NOT NULL
      )
      WHERE rn = 1
    )
  )
)
SELECT
  name                      AS player_name,
  club_name,
  league_name,
  position                  AS tm_position,
  market_value_eur,
  ROUND(raw_wage)           AS raw_predicted_wage_eur_weekly,
  multiplier                AS league_multiplier,
  ROUND(raw_wage * multiplier)      AS predicted_wage_eur_weekly,
  ROUND(raw_wage * multiplier * 52) AS predicted_wage_eur_annual,
  CURRENT_DATE()            AS prediction_date
FROM preds
"""


def run(sql: str, desc: str) -> bigquery.QueryJob:
    log.info("Running: %s", desc)
    job = client.query(sql)
    job.result()
    log.info("Done: %s", desc)
    return job


def main():
    log.info("=== rz-wage-predictor started ===")
    log.info("Project: %s", PROJECT)

    run(SQL_TRAIN, "train ml.wage_regression")

    eval_job = client.query(SQL_EVALUATE)
    for row in eval_job.result():
        log.info(
            "Model evaluation — R²=%.4f  MSE=%.4f  MAE=%.4f",
            row.r2_score,
            row.mean_squared_error,
            row.mean_absolute_error,
        )

    run(SQL_PREDICT, "insert predictions → raw.bqml_wage_predictions")

    count_job = client.query(
        f"SELECT COUNT(*) AS n, "
        f"COUNTIF(league_multiplier < 1.0) AS adjusted, "
        f"ROUND(AVG(predicted_wage_eur_weekly)) AS avg_wage "
        f"FROM `{PROJECT}.raw.bqml_wage_predictions` "
        f"WHERE prediction_date = CURRENT_DATE()"
    )
    for row in count_job.result():
        log.info(
            "Rows inserted: %d (league-adjusted: %d, avg wage: €%.0f/week)",
            row.n, row.adjusted, row.avg_wage or 0,
        )

    log.info("=== rz-wage-predictor complete ===")


if __name__ == "__main__":
    main()
