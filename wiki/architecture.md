# Architecture — Data sources, pipeline, and BigQuery

> **Status:** living document, last updated 2026-06-28. Transfermarkt + SofaScore pipelines built; SofaScore verified working locally, Cloud Run deployment pending.

## Goal

Build a data foundation to:
- **Predict match outcomes** — model Zaragoza fixtures using historical and live form data
- **Evaluate signings** — compare targets against current squad and league-wide benchmarks
- **Scout opponents** — aggregate player and team stats across LaLiga2 and 1RFEF

---

## Data sources

| Source | What | Leagues | Method | Status |
|---|---|---|---|---|
| **Transfermarkt** | Squad, market values, contracts | All (Zaragoza only) | httpx + BeautifulSoup | Live, weekly |
| **SofaScore** | Match results, player stats, team stats, shot maps | LaLiga2 + 1RFEF | curl_cffi (Chrome TLS impersonation) | Verified locally; Cloud Run deployment pending |

**Why SofaScore over FotMob:** FotMob provides only match results (`lower` coverage) for 1RFEF with no player stats. SofaScore has full player and team stats for both LaLiga2 and 1RFEF, making it viable for Zaragoza's 2026-27 season.

---

## SofaScore IDs

| Entity | SofaScore ID |
|---|---|
| LaLiga2 tournament | 54 |
| LaLiga2 2024-25 season | 62048 |
| LaLiga2 2025-26 season | 77558 |
| 1RFEF tournament | 17073 |
| 1RFEF 2024-25 season | 64430 |
| 1RFEF 2025-26 season | 77727 |
| Real Zaragoza team | 2815 |

---

## Cloud infrastructure (GCP project: `real-zaragoza-500608`, region: `europe-west1`)

```
Cloud Scheduler (every Tuesday)
  ├── 06:00 CET → rz-weekly-ingest      → Cloud Run: rz-scraper-transfermarkt
  └── 06:30 CET → rz-weekly-sofascore  → Cloud Run: rz-scraper-sofascore
                                                ↓
                                          BigQuery (rz_raw)
```

| Resource | Name | Purpose |
|---|---|---|
| Cloud Run job | `rz-scraper-transfermarkt` | Scrapes Transfermarkt squad page → `rz_raw.transfermarkt_squad` |
| Cloud Run job | `rz-scraper-sofascore` | Scrapes SofaScore match + player stats → `rz_raw.sofascore_*` tables |
| Cloud Scheduler | `rz-weekly-ingest` | Fires Tuesdays 06:00 CET |
| Cloud Scheduler | `rz-weekly-sofascore` | Fires Tuesdays 06:30 CET |
| BQ dataset | `rz_raw` | Append-only partitioned tables — source of truth |
| BQ dataset | `rz_processed` | Views over `rz_raw` for analysis |
| Service account | `rz-pipeline` | Minimum IAM: BQ dataEditor + jobUser |
| Budget alert | `rz-pipeline-alert` | €10/month cap |
| Artifact Registry | `rz-images` | Container images for Cloud Run jobs |

---

## Historical vs. incremental scraping

**Historical backfill** — run once per season to load a full season's data:
```bash
# Set TOURNAMENT_ID + SEASON_ID for the target season, INCREMENTAL=false (default)
gcloud run jobs update rz-scraper-sofascore \
  --update-env-vars TOURNAMENT_ID=54,SEASON_ID=62048,INCREMENTAL=false
gcloud run jobs execute rz-scraper-sofascore --region europe-west1
```

**Weekly incremental** — default mode once a season is loaded:
- `rz-scraper-sofascore` has `INCREMENTAL=true`; fetches rounds containing matches from last 14 days
- Transfermarkt always scrapes the current squad (append-only)

Seasons to backfill:
- LaLiga2 2024-25 → `TOURNAMENT_ID=54 SEASON_ID=62048`
- LaLiga2 2025-26 → `TOURNAMENT_ID=54 SEASON_ID=77558`
- 1RFEF 2026-27   → season ID not yet created by SofaScore (season starts ~July 2026)

---

## BigQuery schema

All `rz_raw` tables are **append-only** — rows are never updated or deleted.

### `rz_raw.transfermarkt_squad`
Partition: `ingested_date` (date of scrape).

| Field | Type | Description |
|---|---|---|
| `ingested_date` | DATE | Partition key |
| `season_id` | INT64 | Transfermarkt season year (2025 = 2025-26) |
| `player_id` | STRING | Transfermarkt internal ID |
| `name` | STRING | |
| `date_of_birth` | DATE | |
| `jersey_number` | STRING | |
| `position` | STRING | Spanish taxonomy (e.g. `Defensa central`) |
| `age` | INT64 | Age at scrape date |
| `nationality` | STRING | Primary nationality |
| `nationality_all` | STRING | Comma-separated (dual nationals) |
| `height` | STRING | e.g. `1,84m` |
| `foot` | STRING | `Derecho` / `Izquierdo` |
| `joined_date` | DATE | |
| `signed_from` | STRING | Previous club |
| `signing_fee` | STRING | Raw string: `Libre`, `120 mil €`, `?` |
| `contract_expiry` | DATE | |
| `market_value_eur` | INT64 | In EUR |
| `ingested_at` | TIMESTAMP | |

### `rz_raw.sofascore_matches`
Partition: `match_date`. Clustered by: `match_round`, `tournament_id`.

| Field | Type | Description |
|---|---|---|
| `match_id` | STRING | SofaScore event ID |
| `match_date` | DATE | Partition key |
| `match_round` | INT64 | Jornada / round number — cluster key |
| `tournament_id` | STRING | 54 = LaLiga2, 17073 = 1RFEF |
| `season_id` | STRING | e.g. 62048, 77558 |
| `home_team_id` / `away_team_id` | STRING | SofaScore team IDs |
| `home_team_name` / `away_team_name` | STRING | |
| `home_score` / `away_score` | INT64 | |
| `status` | STRING | finished / notstarted / inprogress |
| `ingested_date` | DATE | Audit |
| `ingested_at` | TIMESTAMP | |

### `rz_raw.sofascore_player_match_stats`
Partition: `match_date`. Clustered by: `match_round`, `team_id`.  
One row per player per match (starters + unused subs). `minutes_played=0` for unused subs.

Key fields: `player_id`, `player_name`, `team_id`, `is_home`, `position` (G/D/M/F), `shirt_number`, `is_substitute`, `captain`, `minutes_played`, `goals`, `goal_assists`, `rating` (SofaScore 1–10), `total_passes`, `accurate_passes`, `total_long_balls`, `accurate_long_balls`, `total_crosses`, `key_passes`, `total_shots`, `shots_on_target`, `aerial_won`, `aerial_lost`, `duel_won`, `duel_lost`, `total_tackle`, `won_tackle`, `interceptions`, `total_clearance`, `ball_recovery`, `dispossessed`, `was_fouled`, `fouls`, `touches`, `possession_lost`, `yellow_cards`, `red_cards`, `saves` (GK), `expected_goals` (xG, available in top leagues), `expected_assists`.

Full schema: [`pipeline/bq-schemas/sofascore_player_match_stats.json`](../pipeline/bq-schemas/sofascore_player_match_stats.json)

### `rz_raw.sofascore_shots`
Partition: `match_date`. Clustered by: `match_round`.  
One row per shot attempt.

Key fields: `shot_id`, `match_id`, `player_id`, `player_name`, `is_home`, `minute`, `added_time`, `time_seconds`, `x`/`y` (shot origin, 0–100 pitch coordinates), `goal_mouth_x`/`y`/`z` + `goal_mouth_location` (e.g. `low-right`), `block_x`/`y` (if blocked), `body_part` (right-foot/left-foot/head), `shot_type` (goal/save/miss/blocked), `situation` (assisted/regular/set-piece), `xg` (null for lower leagues).

Full schema: [`pipeline/bq-schemas/sofascore_shots.json`](../pipeline/bq-schemas/sofascore_shots.json)

### `rz_raw.sofascore_team_match_stats`
Partition: `match_date`. Clustered by: `match_round`, `team_id`.  
Two rows per match (home + away).

Key fields: `team_id`, `team_name`, `side`, `possession_pct`, `total_shots`, `shots_on_target`, `shots_off_target`, `blocked_shots`, `shots_on_woodwork`, `shots_inside_box`, `shots_outside_box`, `big_chances`, `big_chances_scored`, `big_chances_missed`, `corners`, `offsides`, `fouls`, `yellow_cards`, `red_cards` — passing: `total_passes`, `accurate_passes`, `accurate_long_balls`, `total_long_balls`, `accurate_crosses`, `total_crosses`, `touches_in_opp_box`, `final_third_entries`, `final_third_acc`, `final_third_total` — defence: `total_tackles`, `won_tackles`, `interceptions`, `clearances`, `ball_recoveries`, `errors_leading_to_shot`, `goalkeeper_saves` — duels: `ground_duels_won`, `total_ground_duels`, `aerial_duels_won`, `total_aerial_duels`, `dribbles_completed`, `total_dribbles`, `dispossessed`.

Full schema: [`pipeline/bq-schemas/sofascore_team_match_stats.json`](../pipeline/bq-schemas/sofascore_team_match_stats.json)

---

## `rz_processed` — views over raw data

**`rz_processed.squad_snapshots`** — most recent Transfermarkt record per `(player_id, season_id)`:
```sql
SELECT * EXCEPT(rn) FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY player_id, season_id ORDER BY ingested_date DESC) AS rn
  FROM `rz_raw.transfermarkt_squad`
) WHERE rn = 1
```

**Planned:** `rz_processed.season_results` — W/D/L, GD, cumulative points per team per season.

---

## Pipeline code

```
pipeline/
  cloud-run/
    scraper_transfermarkt.py     # Transfermarkt scraper
    scraper_sofascore.py         # SofaScore scraper (backfill + incremental)
    Dockerfile                   # Transfermarkt container (python:3.12-slim)
    Dockerfile.sofascore         # SofaScore container (python:3.12-slim + curl_cffi)
    requirements.txt             # Transfermarkt deps
    requirements-sofascore.txt   # SofaScore deps (curl_cffi, pandas, google-cloud-bigquery)
    cloudbuild-sofascore.yaml    # Cloud Build config for SofaScore image
  bq-schemas/
    transfermarkt_squad.json
    sofascore_matches.json
    sofascore_player_match_stats.json
    sofascore_shots.json
    sofascore_team_match_stats.json
```

---

## Notes on Cloud Run vs. local execution

`curl_cffi` bundles its own libcurl binary (no system dependencies). However, **SofaScore blocks GCP datacenter IPs** at the Cloudflare layer — Cloud Run executions get non-200 from every API call even with Chrome TLS impersonation (confirmed 2026-06-28).

**Current execution model:**
- **SofaScore backfills and weekly runs: local machine** — `python3 scraper_sofascore.py` with `GCP_PROJECT_ID` set, writing directly to BigQuery via Application Default Credentials. Home IP is not blocked.
- **Transfermarkt: Cloud Run** — unaffected (static site, no bot protection).
- `rz-scraper-sofascore` Cloud Run job exists but scheduler (`rz-weekly-sofascore`) is **paused**. Kept in case a proxy or alternative approach is added later.

To run a local weekly update (1RFEF season, once it starts):
```bash
cd pipeline/cloud-run
GCP_PROJECT_ID=real-zaragoza-500608 TOURNAMENT_ID=17073 SEASON_ID=<sid> INCREMENTAL=true \
  python3 scraper_sofascore.py
```

---

## Open items

- **Weekly automation** — `rz-weekly-sofascore` scheduler is paused (GCP IPs blocked). Options: (1) local launchd cron on Mac, (2) non-GCP host (DigitalOcean/Fly.io), (3) residential proxy in the Cloud Run image.
- **1RFEF 2026-27** — season ID not yet available on SofaScore; check ~July 2026. Update `SEASON_ID` in weekly local run command above.
- **Dedup view** — `rz_processed.match_dedup` on `(match_id)` keeping latest `ingested_at` (relevant once incremental runs add overlapping rows).
- **`rz_processed.season_results`** — W/D/L, GD, points per team per season from `sofascore_matches` once backfills confirmed.

## Sources

- [SofaScore — sofascore.com](https://www.sofascore.com/es-la/football/tournament/spain/laliga-2/54)
- [Transfermarkt — verein/142/plus/1](https://www.transfermarkt.es/real-zaragoza/kader/verein/142/plus/1)
- [Cloud Run jobs documentation](https://cloud.google.com/run/docs/create-jobs)
- [BigQuery partitioned tables](https://cloud.google.com/bigquery/docs/partitioned-tables)
