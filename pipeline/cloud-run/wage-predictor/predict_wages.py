#!/usr/bin/env python3
"""
rz-wage-predictor — BQML wage prediction pipeline.

Steps per run:
  1. Train/refresh ml.wage_regression on Capology × TM joined data.
  2. Evaluate the model and log R².
  3. Predict wages for every player in silver.tm_players with a known market value.
  4. Append predictions to raw.bqml_wage_predictions (one row per player per run).

Cadence: quarterly (Jan 2 / Apr 2 / Jul 2 / Oct 2) — 1 day after TM scrape so
the model always trains on the freshest market values.
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


def run(sql: str, desc: str) -> bigquery.QueryJob:
    log.info("Running: %s", desc)
    job = client.query(sql)
    job.result()
    log.info("Done: %s", desc)
    return job


# ── 1. Train model ────────────────────────────────────────────────────────────
#
# Training set: Capology wages (top-5 EU, actual gross) joined with TM market
# values on normalised player+club name. ~1,500–2,000 rows after join drop-off.
# Features: log(market_value_eur), position_group (GK/DEF/MID/FWD).
# Label: log(wage_eur_weekly) — log-linear gives better fit across salary ranges.

SQL_TRAIN = f"""
CREATE OR REPLACE MODEL `{PROJECT}.ml.wage_regression`
OPTIONS (
  model_type       = 'linear_reg',
  input_label_cols = ['log_wage_weekly'],
  data_split_method = 'AUTO_SPLIT',
  max_iterations   = 50
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
WHERE c.wage_eur_weekly   > 0
  AND t.market_value_eur  > 0
  AND c.position_group IS NOT NULL
"""

# ── 2. Evaluate ───────────────────────────────────────────────────────────────

SQL_EVALUATE = f"""
SELECT * FROM ML.EVALUATE(MODEL `{PROJECT}.ml.wage_regression`)
"""

# ── 3. Predict and append ─────────────────────────────────────────────────────
#
# Predicts for the latest row per player_id in silver.tm_players (most recent
# market value, regardless of season). position_group is derived from TM's
# granular position field using the same buckets as Capology.
# ML.PREDICT passes through all non-feature columns unchanged.

SQL_PREDICT = f"""
INSERT INTO `{PROJECT}.raw.bqml_wage_predictions`
  (player_name, club_name, league_name, tm_position, market_value_eur,
   predicted_wage_eur_weekly, predicted_wage_eur_annual, prediction_date)
SELECT
  name              AS player_name,
  club_name,
  league_name,
  position          AS tm_position,
  market_value_eur,
  ROUND(EXP(predicted_log_wage_weekly))       AS predicted_wage_eur_weekly,
  ROUND(EXP(predicted_log_wage_weekly) * 52)  AS predicted_wage_eur_annual,
  CURRENT_DATE()                              AS prediction_date
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
"""


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
        f"SELECT COUNT(*) AS n FROM `{PROJECT}.raw.bqml_wage_predictions`"
        f" WHERE prediction_date = CURRENT_DATE()"
    )
    for row in count_job.result():
        log.info("Rows inserted today: %d", row.n)

    log.info("=== rz-wage-predictor complete ===")


if __name__ == "__main__":
    main()
