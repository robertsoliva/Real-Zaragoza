#!/usr/bin/env python3
"""
Player profile clustering — step 1: pull TM-labeled player-seasons, MICE-impute
missing stats within each position group, write the clean feature table to BQ.

Segmentation: TM position (granular), mapped to 7 position groups (CB, FB, DM,
CM, CAM, Winger, CF). Training data is restricted to rows with a real TM
position match (gold.agg_scouting_player_season where tm_position differs from
the SofaScore fallback) and >=450 minutes. GK and the sparse catch-all TM labels
(Centrocampista/Delantero/Defensa, <15 rows each) are out of scope.

Imputation is fit separately per position group (sklearn IterativeImputer) since
feature correlations differ by role -- a CB's touches/tackles relationship isn't
the same as a winger's.

Output: ml.player_profile_features (one row per sofascore_id x team_name x
season_id, position_group + imputed feature columns). Step 2 (BQML training)
reads directly from this table.
"""

import logging
import os
import sys

import pandas as pd
from google.cloud import bigquery
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger(__name__)

PROJECT = os.environ.get("GCP_PROJECT_ID", "real-zaragoza-500608")
LOCATION = "europe-west1"
client = bigquery.Client(project=PROJECT, location=LOCATION)

# Position-specific feature sets. CB/Winger/CF per the agreed next-actions.md design;
# FB/DM/CM/CAM extended in the same style for this build.
FEATURES = {
    "CB":     ["aerial_win_pct", "duel_win_pct", "tackles_p90", "interceptions_p90", "pass_acc_pct", "long_ball_acc_pct"],
    "FB":     ["tackles_p90", "interceptions_p90", "cross_acc_pct", "key_passes_p90", "touches_p90", "duel_win_pct"],
    "DM":     ["tackles_p90", "interceptions_p90", "pass_acc_pct", "duel_win_pct", "touches_p90", "long_ball_acc_pct"],
    "CM":     ["pass_acc_pct", "key_passes_p90", "tackles_p90", "touches_p90", "assists_p90", "duel_win_pct"],
    "CAM":    ["key_passes_p90", "assists_p90", "shots_p90", "goals_p90", "touches_p90", "pass_acc_pct"],
    "Winger": ["shots_p90", "key_passes_p90", "cross_acc_pct", "tackles_p90", "touches_p90"],
    "CF":     ["goals_p90", "shots_p90", "aerial_win_pct", "key_passes_p90", "touches_p90", "tackles_p90"],
}

# TM Spanish-language position label -> our 7 position groups.
TM_POSITION_MAP = {
    "Defensa central": "CB",
    "Lateral derecho": "FB",
    "Lateral izquierdo": "FB",
    "Pivote": "DM",
    "Mediocentro": "CM",
    "Interior derecho": "CM",
    "Interior izquierdo": "CM",
    "Mediocentro ofensivo": "CAM",
    "Mediapunta": "CAM",
    "Extremo derecho": "Winger",
    "Extremo izquierdo": "Winger",
    "Delantero centro": "CF",
}

ID_COLS = ["sofascore_id", "player_name", "team_name", "league_name", "tournament_id", "season_id"]

CASE_SQL = "\n    ".join(
    f"WHEN tm_position = '{tm}' THEN '{grp}'" for tm, grp in TM_POSITION_MAP.items()
)

QUERY = f"""
SELECT
  {', '.join(ID_COLS)},
  CASE
    {CASE_SQL}
    ELSE NULL
  END AS position_group,
  aerial_win_pct, duel_win_pct, tackles_p90, interceptions_p90, pass_acc_pct,
  long_ball_acc_pct, cross_acc_pct, key_passes_p90, touches_p90, assists_p90,
  shots_p90, goals_p90
FROM `{PROJECT}.gold.agg_scouting_player_season`
WHERE sofascore_position != tm_position  -- real TM match, not the SofaScore fallback
  AND total_minutes >= 450
  AND tm_position IN ({', '.join(f"'{k}'" for k in TM_POSITION_MAP)})
"""


def main():
    log.info("Pulling TM-labeled player-seasons from gold.agg_scouting_player_season")
    df = client.query(QUERY).to_dataframe()
    log.info("Pulled %d rows", len(df))

    imputed_frames = []
    for group, feats in FEATURES.items():
        sub = df[df["position_group"] == group].copy()
        if sub.empty:
            log.warning("No rows for position_group=%s, skipping", group)
            continue

        log.info("Imputing %s: %d rows, %d features", group, len(sub), len(feats))
        na_before = sub[feats].isna().sum().sum()

        imputer = IterativeImputer(random_state=42, max_iter=15, sample_posterior=False)
        sub[feats] = imputer.fit_transform(sub[feats])

        na_after = sub[feats].isna().sum().sum()
        log.info("  NULLs before=%d after=%d", na_before, na_after)

        imputed_frames.append(sub[ID_COLS + ["position_group"] + feats])

    out = pd.concat(imputed_frames, ignore_index=True)
    log.info("Total imputed rows: %d", len(out))

    table_id = f"{PROJECT}.ml.player_profile_features"
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    load_job = client.load_table_from_dataframe(out, table_id, job_config=job_config)
    load_job.result()
    log.info("Wrote %d rows to %s", len(out), table_id)


if __name__ == "__main__":
    main()
