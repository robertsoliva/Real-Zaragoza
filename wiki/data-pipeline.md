# Data Pipeline — Ingestion architecture and BigQuery schema

> **Status:** living document, last updated 2026-06-26. Transfermarkt pipeline fully automated: Cloud Run job + Cloud Scheduler (Tuesdays 06:00 CET) live and tested. FotMob scraper built and smoke-tested locally — covers LaLiga2 (Segunda División) 2024-25 full season, all 22 teams, all matches, per-player stats. Cloud Run deployment pending.

## TL;DR

- Sources: Transfermarkt (player/market data) and FotMob (match/stats data), scraped weekly every Tuesday
- Pipeline: Cloud Scheduler → Cloud Run (scraper) → Pub/Sub → Cloud Function → BigQuery
- Two BQ datasets: `rz_raw` (append-only partitioned ingests) and `rz_processed` (cleaned views/tables for analysis)
- `data/` in this repo is for local working snapshots only — BigQuery is the persistence layer; raw files are gitignored
- Service account key is never committed — use Secret Manager or Cloud Run env vars

## Model

**Type:** Infrastructure  
**Relationships:**
- [squad.md](./squad.md) — Transfermarkt feed is the primary source for player roster and market values
- [academy.md](./academy.md) — Transfermarkt feed will replace the dated 2018–19 academy graduate list with a current one
- [records.md](./records.md) — SofaScore match data will feed the season-by-season results table and statistical records
- [history.md](./history.md) — SofaScore historical results will power the season-by-season table flagged as open item there

## Architecture

### Pipeline flow

```
Cloud Scheduler (every Tuesday, 06:00 CET)
  ↓
Cloud Run — rz-scraper (container job)
  scrapes Transfermarkt: squad, market values, contracts
  scrapes SofaScore: recent matches, team stats, player stats
  publishes one Pub/Sub message per data type
  ↓
Pub/Sub topic: rz-data-ingested
  ↓
Cloud Function — rz-bq-loader
  triggered by Pub/Sub push subscription
  validates schema
  streams rows into BigQuery (rz_raw dataset)
```

### Why Pub/Sub between Cloud Run and Cloud Function

Cloud Run (scraper) and Cloud Function (BQ writer) are decoupled deliberately:
- If a BQ write fails, Pub/Sub retries automatically — no re-scraping needed
- Future consumers (Slack alerts, wiki auto-update triggers) subscribe to the same topic without touching the scraper
- Each data type (squad snapshot, match results, player stats) is an independent message — a partial failure doesn't block the rest

### GCP resource map

| Resource | Name | Status | Purpose |
|---|---|---|---|
| Cloud Scheduler job | `rz-weekly-ingest` | **live** | Fires every Tuesday 06:00 CET, triggers Cloud Run |
| Cloud Run job | `rz-scraper-transfermarkt` | **live** | Scrapes Transfermarkt, writes directly to BQ |
| Cloud Run job | `rz-scraper-fotmob` | pending deploy | Scrapes FotMob LaLiga2 matches + player stats |
| Pub/Sub topic | `rz-data-ingested` | **live** | Message bus; decouples scrape from load |
| Pub/Sub dead-letter topic | `rz-data-ingested-dlq` | **live** | Catches failed messages for inspection |
| Cloud Function | `rz-bq-loader` | pending | Pub/Sub subscriber; writes to BQ |
| BQ dataset | `rz_raw` | **live** | Append-only raw ingests, partitioned by `ingested_date` |
| BQ dataset | `rz_processed` | **live** | Cleaned/transformed tables and views for analysis |
| Service account | `rz-pipeline` | **live** | Minimum IAM: BQ dataEditor+jobUser, Pub/Sub publisher+subscriber |
| Budget alert | `rz-pipeline-alert` | **live** | €10/month cap; alerts at 50%, 90%, 100% |

## BigQuery schema

All `rz_raw` tables are append-only — existing rows are never updated. Analysis always queries the latest partition or aggregates across partitions.

### `rz_raw.transfermarkt_squad`
Weekly squad snapshot. Partitioned by `ingested_date`. Schema confirmed against live page (verein/142, `/plus/1`, Spanish domain).

| Field | Type | Notes |
|---|---|---|
| `ingested_date` | DATE | Partition key |
| `season_id` | INT64 | Transfermarkt season year (e.g. 2025 = 2025-26 season) |
| `player_id` | STRING | Transfermarkt internal player ID |
| `name` | STRING | Full player name |
| `date_of_birth` | DATE | ISO date; extracted from `DD/MM/YYYY (AGE)` cell |
| `jersey_number` | STRING | Current squad number (`-` if unassigned) |
| `position` | STRING | Transfermarkt Spanish position taxonomy (e.g. `Defensa central`) |
| `age` | INT64 | Age at scrape date |
| `nationality` | STRING | Primary nationality (first flag) |
| `nationality_all` | STRING | Comma-separated list for dual nationals |
| `height` | STRING | Height as reported, e.g. `1,84m` |
| `foot` | STRING | `Derecho` / `Izquierdo`; null if not listed |
| `joined_date` | DATE | Date player joined the club |
| `signed_from` | STRING | Previous club name |
| `signing_fee` | STRING | Raw fee string e.g. `Libre`, `120 mil €`, `?` |
| `contract_expiry` | DATE | Contract expiry date |
| `market_value_eur` | INT64 | Market value in EUR (Spanish format parsed: `mill.` = ×1M, `mil` = ×1K) |
| `ingested_at` | TIMESTAMP | UTC load timestamp |

### `rz_raw.fotmob_matches`
One row per match. Partitioned by `ingested_date`. FotMob leagueId=893055 (LaLiga2).

| Field | Type | Notes |
|---|---|---|
| `match_id` | STRING | FotMob internal ID |
| `ingested_date` | DATE | Partition key |
| `league_id` | STRING | 893055 for LaLiga2 |
| `league_name` | STRING | |
| `parent_league_id` | STRING | 140 for Segunda |
| `match_time_utc` | STRING | ISO UTC kickoff |
| `match_date` | DATE | Calendar date of match |
| `match_round` | STRING | League matchday |
| `home_team_id` | STRING | |
| `home_team_name` | STRING | |
| `away_team_id` | STRING | |
| `away_team_name` | STRING | |
| `home_score` | INT64 | |
| `away_score` | INT64 | |
| `coverage_level` | STRING | `xG` / `ratings` / `lower` |
| `ingested_at` | TIMESTAMP | |

### `rz_raw.fotmob_player_match_stats`
One row per player per match. Only populated for `ratings` or `xG` coverage matches.

| Field | Type | Notes |
|---|---|---|
| `match_id` | STRING | FK → fotmob_matches |
| `player_id` | STRING | FotMob player ID |
| `ingested_date` | DATE | Partition key |
| `player_name` | STRING | |
| `team_id` | STRING | |
| `team_name` | STRING | |
| `is_goalkeeper` | BOOL | |
| `shirt_number` | STRING | |
| `usual_position` | INT64 | FotMob position code |
| `minutes_played` | INT64 | |
| `goals` | INT64 | |
| `assists` | INT64 | |
| `rating` | FLOAT64 | FotMob match rating (0–10) |
| `expected_assists` | FLOAT64 | xA — xG coverage only |
| `xg_and_xa` | FLOAT64 | xG+xA — xG coverage only |
| `accurate_passes` | INT64 | |
| `total_passes` | INT64 | |
| `chances_created` | INT64 | |
| `defensive_actions` | INT64 | |
| `touches` | INT64 | |
| `touches_opp_box` | INT64 | |
| `passes_into_final_third` | INT64 | |
| `long_balls_accurate` | INT64 | |
| `long_balls_total` | INT64 | |
| `dispossessed` | INT64 | |
| `tackles` | INT64 | |
| `blocks` | INT64 | |
| `clearances` | INT64 | |
| `headed_clearances` | INT64 | |
| `interceptions` | INT64 | |
| `recoveries` | INT64 | |
| `dribbled_past` | INT64 | |
| `ground_duels_won` | INT64 | |
| `ground_duels_total` | INT64 | |
| `aerial_duels_won` | INT64 | |
| `aerial_duels_total` | INT64 | |
| `was_fouled` | INT64 | |
| `fouls_committed` | INT64 | |
| `ingested_at` | TIMESTAMP | |

### `rz_raw.fotmob_shots`
One row per shot attempt. Only populated for `xG` coverage matches (shot coordinates + xG values available).

| Field | Type | Notes |
|---|---|---|
| `shot_id` | STRING | FotMob shot event ID |
| `match_id` | STRING | FK → fotmob_matches |
| `ingested_date` | DATE | Partition key |
| `team_id` | STRING | |
| `player_id` | STRING | |
| `player_name` | STRING | |
| `event_type` | STRING | Goal / Miss / SavedShot / BlockedShot |
| `shot_type` | STRING | Header / LeftFoot / RightFoot |
| `situation` | STRING | RegularPlay / SetPiece / etc |
| `period` | STRING | FirstHalf / SecondHalf / ExtraTime* |
| `minute` | INT64 | |
| `minute_added` | INT64 | |
| `x` | FLOAT64 | Shot origin x (pitch %) |
| `y` | FLOAT64 | Shot origin y (pitch %) |
| `expected_goals` | FLOAT64 | xG of this shot |
| `expected_goals_on_target` | FLOAT64 | xGoT |
| `is_on_target` | BOOL | |
| `is_blocked` | BOOL | |
| `is_own_goal` | BOOL | |
| `new_score_home` | INT64 | Home score after this event (goals only) |
| `new_score_away` | INT64 | |
| `ingested_at` | TIMESTAMP | |

**FotMob coverage notes:**  
LaLiga2 matches have `ratings` coverage for older matches and `xG` coverage for recent/prominent ones. `xG` level gives shot coordinates, xG, xA values. `ratings` level gives the full player stat suite but no xG or shot map. Both levels provide: rating, minutes, goals, assists, passes, chances created, touches, defensive stats, duels.

### `rz_processed` — historical strategy

`rz_raw.transfermarkt_squad` is append-only: every weekly scrape adds ~32 rows. Over a season this produces ~1,600 rows, all of them valid snapshots. The processed layer deduplcates via views — no MERGE or TRUNCATE needed.

**Why not TRUNCATE + INSERT?** Departed players are permanently lost.  
**Why not UPSERT on `player_id` only?** A player re-signed two seasons later overwrites their old record.  
**Solution:** `season_id` acts as a historical partition. A MERGE keyed on `(player_id, season_id)` would work, but a view over the raw table is simpler and gives the same result without any write logic.

#### `rz_processed.squad_snapshots` (view)
One row per `(player_id, season_id)` — always the most recent scrape for that combination.

```sql
SELECT * EXCEPT(rn)
FROM (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY player_id, season_id
      ORDER BY ingested_date DESC
    ) AS rn
  FROM `rz_raw.transfermarkt_squad`
)
WHERE rn = 1
```

| Query pattern | How |
|---|---|
| Current squad | `WHERE season_id = 2025` |
| Historical squad (e.g. 2023) | `WHERE season_id = 2023` |
| Players who left between seasons | LEFT JOIN 2024 vs 2025 on `player_id`, filter WHERE 2025.player_id IS NULL |
| Value progression per player | JOIN across seasons on `player_id`, ORDER BY season_id |
| Intra-season value changes | Query `rz_raw` directly, filter by `player_id` + date range |

#### `rz_processed.player_valuations` (view)
Time series of market value per player — one row per `(player_id, ingested_date)`. Useful for tracking value changes within and across seasons.

#### `rz_processed.season_results` (planned)
Cleaned match results from SofaScore with computed W/D/L, goal difference, and cumulative points. Pending SofaScore scraper.

## Local `data/` directory

`data/` is for local dev snapshots only — useful for iterating on schemas without hitting the live API every time. Not the persistence layer.

```
data/
  raw/
    transfermarkt/   # raw JSON/CSV (gitignored)
    sofascore/       # raw JSON/CSV (gitignored)
  processed/         # locally transformed outputs (gitignored)
```

The directory structure is tracked (via `.gitkeep` files); the contents are not.

## `pipeline/` directory

Source code lives in `pipeline/` once implementation begins:

```
pipeline/
  cloud-run/         # rz-scraper container (Dockerfile + scraper code)
  cloud-function/    # rz-bq-loader function code
```

## Service account

Minimum required IAM roles:

| Role | Why |
|---|---|
| `roles/bigquery.dataEditor` | Write rows to `rz_raw` and `rz_processed` |
| `roles/pubsub.publisher` | Cloud Run publishes to `rz-data-ingested` |
| `roles/pubsub.subscriber` | Cloud Function subscribes to the topic |

The service account key file is **never committed to this repo**. Options:
- Store in GCP Secret Manager and mount into Cloud Run at runtime
- Pass as `GOOGLE_APPLICATION_CREDENTIALS` env var in Cloud Run config (not hardcoded)

## Open items

- **FotMob Cloud Run deployment** — build `Dockerfile.fotmob` via Cloud Build, push to Artifact Registry as `rz-scraper-fotmob`, run one-off job for 2024-25 historical backfill, then add to Cloud Scheduler for weekly 2025-26 updates
- **FotMob scraper: season scope** — currently hard-coded to 2024-25. After historical backfill, update to scrape 2025-26 incrementally (matches since last run only). Add a `last_match_date` checkpoint or query BQ for the most recent `match_date` already loaded.
- **FotMob: 1RFEF coverage** — Primera Federación matches have `lower` coverage in FotMob (no player stats, no lineup, no team stats). Match results only. Not worth scraping until FotMob improves coverage.
- **DLQ handling** — define what happens when a message in `rz-data-ingested-dlq` is not resolved (manual replay vs. auto-retry limit)
- **`rz_processed.player_valuations` view** — time-series of market value per player; add once a second weekly scrape lands so there's actual change data to query
- **`rz_processed.season_results`** — planned: cleaned match results from `fotmob_matches` with W/D/L, goal difference, cumulative points
- **Cloud Monitoring alerts** — Pub/Sub subscription backlog + Cloud Function error rate; set up when Cloud Function is deployed

## Sources

- [Cloud Run jobs documentation — Google](https://cloud.google.com/run/docs/create-jobs)
- [Cloud Scheduler documentation — Google](https://cloud.google.com/scheduler/docs)
- [Pub/Sub documentation — Google](https://cloud.google.com/pubsub/docs)
- [BigQuery documentation — Google](https://cloud.google.com/bigquery/docs)
- [google-cloud-bigquery Python SDK](https://cloud.google.com/python/docs/reference/bigquery/latest)
