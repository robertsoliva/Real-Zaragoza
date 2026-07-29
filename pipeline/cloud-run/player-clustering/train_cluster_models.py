#!/usr/bin/env python3
"""
Player profile clustering — step 2: train one BQML k-means model per position
group, with native hyperparameter tuning over num_clusters (k=2..8) to avoid
pre-defining k. BQML has no native silhouette score for unsupervised models,
so it picks the best trial via Davies-Bouldin index (lower = better-separated,
more compact clusters) -- same empirical intent as the original elbow +
silhouette plan, different metric.

Reads from ml.player_profile_features (written by impute_player_features.py).
"""

import logging
import os
import sys

from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger(__name__)

PROJECT = os.environ.get("GCP_PROJECT_ID", "real-zaragoza-500608")
LOCATION = "europe-west1"
client = bigquery.Client(project=PROJECT, location=LOCATION)

FEATURES = {
    "CB":     ["aerial_win_pct", "duel_win_pct", "tackles_p90", "interceptions_p90", "pass_acc_pct", "long_ball_acc_pct"],
    "FB":     ["tackles_p90", "interceptions_p90", "cross_acc_pct", "key_passes_p90", "touches_p90", "duel_win_pct"],
    "DM":     ["tackles_p90", "interceptions_p90", "pass_acc_pct", "duel_win_pct", "touches_p90", "long_ball_acc_pct"],
    "CM":     ["pass_acc_pct", "key_passes_p90", "tackles_p90", "touches_p90", "assists_p90", "duel_win_pct"],
    "CAM":    ["key_passes_p90", "assists_p90", "shots_p90", "goals_p90", "touches_p90", "pass_acc_pct"],
    "Winger": ["shots_p90", "key_passes_p90", "cross_acc_pct", "tackles_p90", "touches_p90"],
    "CF":     ["goals_p90", "shots_p90", "aerial_win_pct", "key_passes_p90", "touches_p90", "tackles_p90"],
}

MODEL_NAME = {
    "CB": "player_cluster_cb", "FB": "player_cluster_fb", "DM": "player_cluster_dm",
    "CM": "player_cluster_cm", "CAM": "player_cluster_cam", "Winger": "player_cluster_winger",
    "CF": "player_cluster_cf",
}


def train(group, feats):
    model = f"{PROJECT}.ml.{MODEL_NAME[group]}"
    cols = ", ".join(feats)
    sql = f"""
    CREATE OR REPLACE MODEL `{model}`
    OPTIONS(
      model_type = 'kmeans',
      num_clusters = hparam_range(2, 8),
      num_trials = 7,
      standardize_features = true
    ) AS
    SELECT {cols}
    FROM `{PROJECT}.ml.player_profile_features`
    WHERE position_group = '{group}'
    """
    log.info("Training %s (%d features)...", model, len(feats))
    job = client.query(sql)
    job.result()
    log.info("  done: %s", model)


def main():
    for group, feats in FEATURES.items():
        train(group, feats)
    log.info("All 7 models trained.")


if __name__ == "__main__":
    main()
