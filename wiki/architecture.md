# Architecture — Data sources, pipeline, and BigQuery

> **Status:** living document, last updated 2026-06-26. Transfermarkt + FotMob pipelines fully automated. 1RFEF coverage pending alternative source (FotMob only provides match results for that tier).

## Goal

Build a data foundation to:
- **Predict match outcomes** — model Zaragoza fixtures using historical and live form data
- **Evaluate signings** — compare targets against current squad and league-wide benchmarks
- **Scout opponents** — aggregate player and team stats across Segunda División and 1RFEF

---

## Data sources

| Source | What | Leagues | Method | Status |
|---|---|---|---|---|
| **Transfermarkt** | Squad, market values, contracts | All (Zaragoza only) | httpx + BeautifulSoup | Live, weekly |
| **FotMob** | Match results, player stats, shot maps | LaLiga2 (Segunda) | Playwright + FotMob API | Live, weekly |
| **FotMob (1RFEF)** | Match results only — no player stats | 1RFEF | Same | Coverage gap — see Open items |
| **TBD** | Full 1RFEF player stats | 1RFEF | SofaScore/FBRef/API-Football | Pending |

**FotMob coverage levels** (determined per match by FotMob):
- `xG` — full stats + shot coordinates + xG/xA per player
- `ratings` — full stats (rating, mins, goals, assists, all defensive/attack stats) — no xG
- `lower` — result only; no player stats available (affects 1RFEF and lower divisions)

LaLiga2 matches are `ratings` or `xG`. 1RFEF matches are always `lower`.

---

## Cloud infrastructure (GCP project: `real-zaragoza-500608`, region: `europe-west1`)

```
Cloud Scheduler (every Tuesday)
  ├── 06:00 CET → rz-weekly-ingest   → Cloud Run: rz-scraper-transfermarkt
  └── 06:30 CET → rz-weekly-fotmob  → Cloud Run: rz-scraper-fotmob
                                              ↓
                                        BigQuery (rz_raw)
```

| Resource | Name | Purpose |
|---|---|---|
| Cloud Run job | `rz-scraper-transfermarkt` | Scrapes Transfermarkt squad page, writes to `rz_raw.transfermarkt_squad` |
| Cloud Run job | `rz-scraper-fotmob` | Scrapes FotMob match + player stats, writes to `rz_raw.fotmob_*` tables |
| Cloud Scheduler | `rz-weekly-ingest` | Fires Tuesdays 06:00 CET |
| Cloud Scheduler | `rz-weekly-fotmob` | Fires Tuesdays 06:30 CET |
| Pub/Sub topic | `rz-data-ingested` | Reserved for future fan-out (Slack alerts, etc.) — not yet wired |
| BQ dataset | `rz_raw` | Append-only partitioned tables — source of truth |
| BQ dataset | `rz_processed` | Views over `rz_raw` for analysis |
| Service account | `rz-pipeline` | Minimum IAM: BQ dataEditor + jobUser, Pub/Sub publisher |
| Budget alert | `rz-pipeline-alert` | €10/month cap |
| Artifact Registry | `rz-images` | Container images for Cloud Run jobs |

---

## Historical vs. incremental scraping

**Historical backfill** — run once per season to load a full season's data:
```bash
# Cloud Run job, INCREMENTAL=false (default), set SCRAPE_START + SCRAPE_END to override dates
gcloud run jobs update rz-scraper-fotmob --update-env-vars INCREMENTAL=false
gcloud run jobs execute rz-scraper-fotmob --region europe-west1
```

**Weekly incremental** — default mode once a season is loaded:
- `rz-scraper-fotmob` has `INCREMENTAL=true` set; fetches last 8 days only
- Transfermarkt always scrapes the current squad (no history needed — BQ is append-only)
- Backfills loaded to date: **LaLiga2 2024-25** (full season, executed 2026-06-26)

To backfill a new season: set `SCRAPE_START=YYYY-MM-DD` + `SCRAPE_END=YYYY-MM-DD` env vars, execute once, then switch back to `INCREMENTAL=true`.

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
| `market_value_eur` | INT64 | In EUR, parsed from Spanish format (`mill.` / `mil`) |
| `ingested_at` | TIMESTAMP | |

### `rz_raw.fotmob_matches`
Partition: `match_date`. Clustered by: `match_round`, `league_id`.

| Field | Type | Description |
|---|---|---|
| `match_id` | STRING | FotMob ID |
| `match_date` | DATE | Partition key — actual match date |
| `match_round` | INT64 | Jornada / matchday number — cluster key |
| `league_id` | STRING | 893055 = LaLiga2 |
| `home_team_id` / `away_team_id` | STRING | FotMob team IDs |
| `home_team_name` / `away_team_name` | STRING | |
| `home_score` / `away_score` | INT64 | |
| `coverage_level` | STRING | `xG` / `ratings` / `lower` |
| `ingested_date` | DATE | Audit — date row was written |
| `ingested_at` | TIMESTAMP | |

### `rz_raw.fotmob_player_match_stats`
Partition: `match_date`. Clustered by: `match_round`, `team_id`.  
One row per player per match. Only populated for `ratings`/`xG` coverage matches.

Key fields: `player_id`, `player_name`, `team_id`, `match_round`, `minutes_played`, `goals`, `assists`, `rating`, `expected_assists` (xA, xG only), `xg_and_xa` (xG only), `accurate_passes` / `total_passes`, `chances_created`, `touches`, `touches_opp_box`, `passes_into_final_third`, `tackles`, `blocks`, `clearances`, `interceptions`, `recoveries`, `ground_duels_won` / `total`, `aerial_duels_won` / `total`, `fouls_committed`, `was_fouled`.

Full schema: [`pipeline/bq-schemas/fotmob_player_match_stats.json`](../pipeline/bq-schemas/fotmob_player_match_stats.json)

### `rz_raw.fotmob_shots`
Partition: `match_date`. Clustered by: `match_round`, `team_id`.  
One row per shot. Only for `xG`-coverage matches.

Key fields: `shot_id`, `match_id`, `player_id`, `event_type` (Goal/Miss/SavedShot/BlockedShot), `shot_type` (Header/LeftFoot/RightFoot), `situation`, `minute`, `x`/`y` (pitch coordinates), `expected_goals`, `expected_goals_on_target`, `is_on_target`, `is_blocked`.

Full schema: [`pipeline/bq-schemas/fotmob_shots.json`](../pipeline/bq-schemas/fotmob_shots.json)

### `rz_raw.fotmob_team_match_stats`
Partition: `match_date`. Clustered by: `match_round`, `team_id`.  
Two rows per match (one per team: `side = home | away`). Populated for `ratings` and `xG` coverage matches (not `lower`).

Key fields: `team_id`, `team_name`, `side`, `possession_pct`, `total_shots`, `shots_on_target`, `shots_off_target`, `blocked_shots`, `shots_inside_box`, `shots_outside_box`, `big_chances`, `big_chances_missed`, `touches_opp_box` — xG only: `xg`, `xg_open_play`, `xg_set_play`, `xg_non_penalty`, `xg_on_target` — passing: `total_passes`, `accurate_passes`, `pass_accuracy_pct`, `own_half_passes`, `opp_half_passes`, `long_balls_accurate`, `long_ball_accuracy_pct`, `accurate_crosses`, `cross_accuracy_pct`, `throws`, `offsides`, `corners` — defence: `tackles`, `interceptions`, `blocks`, `clearances`, `keeper_saves` — duels/dribbles: `duels_won`, `ground_duels_won`, `ground_duel_pct`, `aerial_duels_won`, `aerial_duel_pct`, `successful_dribbles`, `dribble_success_pct` — discipline: `yellow_cards`, `red_cards`, `fouls_committed`.

Full schema: [`pipeline/bq-schemas/fotmob_team_match_stats.json`](../pipeline/bq-schemas/fotmob_team_match_stats.json)

---

## `rz_processed` — views over raw data

**`rz_processed.squad_snapshots`** — most recent Transfermarkt record per `(player_id, season_id)`:
```sql
SELECT * EXCEPT(rn) FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY player_id, season_id ORDER BY ingested_date DESC) AS rn
  FROM `rz_raw.transfermarkt_squad`
) WHERE rn = 1
```

**Planned:** `rz_processed.season_results` — cleaned match results with W/D/L, GD, cumulative points per team per season.

---

## Pipeline code

```
pipeline/
  cloud-run/
    scraper_transfermarkt.py   # Transfermarkt scraper
    scraper_fotmob.py          # FotMob scraper (supports backfill + incremental)
    Dockerfile                 # Transfermarkt container (python:3.12-slim)
    Dockerfile.fotmob          # FotMob container (playwright/python base image)
    requirements.txt           # Transfermarkt deps
    requirements-fotmob.txt    # FotMob deps
  bq-schemas/
    transfermarkt_squad.json
    fotmob_matches.json
    fotmob_player_match_stats.json
    fotmob_shots.json
    fotmob_team_match_stats.json
    cloudbuild-fotmob.yaml       # Cloud Build config for FotMob image
```

---

## Open items

- **1RFEF player stats** — FotMob only provides match results for 1RFEF (`lower` coverage). Zaragoza play in 1RFEF from 2026-27. Options in priority order: (1) test SofaScore from Cloud Run IPs (different from home IP that was blocked), (2) FBRef scraper (free, has 1RFEF), (3) API-Football (paid, has 1RFEF).
- **LaLiga2 2025-26 backfill** — Zaragoza's current season just ended (May 2026). Run `SCRAPE_START=2025-07-01 SCRAPE_END=2026-06-26` to backfill. Weekly incremental picks up from today onward.
- **`rz_processed.season_results`** — build view once FotMob data confirmed in BQ.
- **Deduplication for incremental** — append-only means the same match can land twice if the 8-day window overlaps. Add dedup view on `(match_id)` in `rz_processed`.

## Sources

- [FotMob API — unofficial, reverse-engineered](https://www.fotmob.com)
- [Transfermarkt — verein/142/plus/1 (Spanish domain)](https://www.transfermarkt.es/real-zaragoza/kader/verein/142/plus/1)
- [Cloud Run jobs documentation](https://cloud.google.com/run/docs/create-jobs)
- [BigQuery partitioned tables](https://cloud.google.com/bigquery/docs/partitioned-tables)
