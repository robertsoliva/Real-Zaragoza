> **Status:** Living document. Last updated 2026-07-26.

# Wage Model

Estimates gross weekly wages for players across all pipeline leagues. Actual wages are only publicly reported for the top-5 EU leagues; this model extends coverage to LaLiga2, Serie B, lower divisions, and MLS via a BigQuery ML regression trained on the players where real data exists.

---

## Why it exists

Scouting reports need a wage sense-check even for lower-league targets. If a LaLiga2 forward has a €3M TM market value and a projected €12k/week wage, and Zaragoza's cap is €8k/week for that slot, that's a useful filter before a call is made. The model makes this possible without requiring access to private contract data.

---

## Data sources

| Source | Coverage | Cadence |
|---|---|---|
| **Capology** (`silver.capology_wages`) | ~2,500 players, Premier League / La Liga / Bundesliga / Ligue 1 / Serie A | Quarterly (Jan/Apr/Jul/Oct 1) |
| **Transfermarkt** (`silver.tm_players`) | ~10,000+ players, all 25 pipeline leagues | Quarterly (Jan/Apr/Jul/Oct 1) |
| **BQML predictions** (`raw.bqml_wage_predictions`) | All TM players with a known market value | Quarterly (Jan/Apr/Jul/Oct **2**) |

The prediction job runs 1 day after the TM scrape so the model always trains on the latest market values.

---

## Model

**Type:** `linear_reg` (BigQuery ML)

**Label:** `log(wage_eur_weekly)` — log-linear captures the nonlinear relationship between salary and market value across the full range (€1k/week second division → €200k/week elite).

**Features:**
- `log(market_value_eur)` — primary predictor; explains ~75-80% of wage variance in top leagues
- `position_group` — GK / DEF / MID / FWD (categorical); captures systematic salary differences by position

**Training set:** inner join of `silver.capology_wages` × `silver.tm_players` on normalised player+club name. Approximately 1,500–2,000 rows after name-matching drop-off (~30%). All rows from the top-5 EU leagues.

**Training dataset:** `real-zaragoza-500608.ml` — BigQuery dataset dedicated to ML models. Model stored as `ml.wage_regression`.

---

## Limitations

- **Top-5 EU data only in training.** The model has never seen a LaLiga2 or Serie B contract; it extrapolates based on market value. Lower-league predictions are systematically biased upward — a player worth €500k at a LaLiga2 club earns less per week than a €500k player at Real Madrid B.
- **Name matching.** ~30% of players fail the Capology × TM name join (diacritics, short names, different transliterations). Those players are excluded from training.
- **Market value lag.** TM values are quarterly snapshots. Mid-window transfers or form spikes aren't reflected until the next scrape.
- **No contract length.** Two players can have identical market values but very different wages depending on contract length and signing bonuses.

All predictions carry `wage_source = 'bqml_estimate'` in `gold.agg_scouting_player_season`. Scouting reports must surface this flag.

---

## Pipeline

```
silver.capology_wages  ──┐
                          ├── ML.TRAIN → ml.wage_regression
silver.tm_players      ──┘
                                │
                          ML.PREDICT on all TM players with market_value > 0
                                │
                          raw.bqml_wage_predictions  (append-only)
                                │
                          silver.bqml_wages  (dbt, latest per player+club)
                                │
                          gold.agg_scouting_player_season
                            wage_eur_weekly  = COALESCE(capology, bqml)
                            wage_source      = 'capology_actual' | 'bqml_estimate'
```

**Cloud Run Job:** `rz-wage-predictor` (europe-west1)  
**Scheduler:** `rz-wage-predictor-quarterly` — cron `30 0 2 1,4,7,10 *` (Jan 2 / Apr 2 / Jul 2 / Oct 2, 00:30 Europe/Madrid)  
**Image:** `europe-west1-docker.pkg.dev/real-zaragoza-500608/rz-images/rz-wage-predictor:latest`  
**Source:** `pipeline/cloud-run/wage-predictor/predict_wages.py`

---

## Wage evolution tracking

Because `raw.bqml_wage_predictions` is append-only, each quarterly run adds a new set of rows with the current `prediction_date`. This means you can track how the predicted wage for a player changes as their market value rises or falls:

```sql
SELECT prediction_date, predicted_wage_eur_weekly
FROM `real-zaragoza-500608.raw.bqml_wage_predictions`
WHERE LOWER(player_name) = 'player name'
  AND LOWER(club_name)   = 'club name'
ORDER BY prediction_date
```

`silver.bqml_wages` always shows the latest prediction; the raw table holds the full history.

---

## Open items

- Lower-league discount factor: apply a league-tier multiplier post-prediction to correct the upward bias for non-top-5-EU players (e.g. LaLiga2 ≈ 35% of La Liga salary for equivalent market value). Requires research into published aggregate salary data per division.
- Model versioning: currently `CREATE OR REPLACE` overwrites the model on each run. Add a version tag to `raw.bqml_wage_predictions` if historical model performance comparison is needed.

---

## Sources

- [Capology](https://www.capology.com/) — reported gross wages, top-5 EU leagues
- [Transfermarkt](https://www.transfermarkt.com/) — market values, all pipeline leagues
- BigQuery ML documentation — [linear regression](https://cloud.google.com/bigquery/docs/linear-regression-tutorial)
