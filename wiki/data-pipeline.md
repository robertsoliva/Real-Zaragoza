# Data Pipeline — Ingestion architecture and BigQuery schema

> **Status:** living document, last updated 2026-06-26. Architecture decided, code not yet written — this page is the specification. Update in place as implementation decisions are made and schemas are confirmed against actual API responses.

## TL;DR

- Sources: Transfermarkt (player/market data) and SofaScore (match/stats data), scraped weekly every Tuesday
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

| Resource | Planned name | Purpose |
|---|---|---|
| Cloud Scheduler job | `rz-weekly-ingest` | Fires every Tuesday, triggers Cloud Run |
| Cloud Run job | `rz-scraper` | Scrapes both sources, publishes to Pub/Sub |
| Pub/Sub topic | `rz-data-ingested` | Message bus; decouples scrape from load |
| Pub/Sub dead-letter topic | `rz-data-ingested-dlq` | Catches failed messages for inspection |
| Cloud Function | `rz-bq-loader` | Pub/Sub subscriber; writes to BQ |
| BQ dataset | `rz_raw` | Append-only raw ingests, partitioned by `ingested_date` |
| BQ dataset | `rz_processed` | Cleaned/transformed tables and views for analysis |

## BigQuery schema

All `rz_raw` tables are append-only — existing rows are never updated. Analysis always queries the latest partition or aggregates across partitions.

### `rz_raw.transfermarkt_squad`
Weekly squad snapshot. Partitioned by `ingested_date`.

| Field | Type | Notes |
|---|---|---|
| `ingested_date` | DATE | Partition key |
| `player_id` | STRING | Transfermarkt internal ID |
| `name` | STRING | Full player name |
| `position` | STRING | Transfermarkt position taxonomy |
| `age` | INT64 | Age at scrape date |
| `nationality` | STRING | Primary nationality |
| `market_value_eur` | INT64 | Market value in EUR |
| `contract_expiry` | DATE | Contract expiry date |
| `status` | STRING | e.g. "active", "on loan", "injured" |
| `ingested_at` | TIMESTAMP | Load timestamp |

### `rz_raw.sofascore_matches`
One row per match. Partitioned by `match_date`.

| Field | Type | Notes |
|---|---|---|
| `match_id` | STRING | SofaScore internal ID |
| `match_date` | DATE | Partition key |
| `competition` | STRING | e.g. "Primera RFEF" |
| `season` | STRING | e.g. "2026-27" |
| `home_team` | STRING | |
| `away_team` | STRING | |
| `home_score` | INT64 | |
| `away_score` | INT64 | |
| `venue` | STRING | |
| `ingested_at` | TIMESTAMP | |

### `rz_raw.sofascore_match_stats`
One row per team per match (2 rows per match_id).

| Field | Type | Notes |
|---|---|---|
| `match_id` | STRING | FK → sofascore_matches |
| `team` | STRING | |
| `xg` | FLOAT64 | Expected goals |
| `possession_pct` | FLOAT64 | |
| `shots` | INT64 | |
| `shots_on_target` | INT64 | |
| `corners` | INT64 | |
| `fouls` | INT64 | |
| `ingested_at` | TIMESTAMP | |

### `rz_raw.sofascore_player_stats`
One row per player per match.

| Field | Type | Notes |
|---|---|---|
| `match_id` | STRING | FK → sofascore_matches |
| `player_id` | STRING | SofaScore internal ID |
| `player_name` | STRING | |
| `minutes_played` | INT64 | |
| `goals` | INT64 | |
| `assists` | INT64 | |
| `rating` | FLOAT64 | SofaScore match rating (0–10) |
| `yellow_cards` | INT64 | |
| `red_cards` | INT64 | |
| `ingested_at` | TIMESTAMP | |

### `rz_processed` (planned)

| Table/view | Description |
|---|---|
| `squad_current` | Latest squad snapshot — filters `transfermarkt_squad` for most recent `ingested_date` |
| `player_valuations` | Time series of market value per player across all ingested dates |
| `season_results` | Cleaned match results with computed W/D/L, goal diff, and cumulative points |

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

- Confirm scraping strategy for each source: Transfermarkt has no public API (HTML scraping or `transfermarkt-scraper` library); SofaScore has an unofficial internal API (reverse-engineered endpoints, rate-limit sensitive)
- Decide base language for Cloud Run container (Python strongly preferred given `google-cloud-bigquery` SDK maturity)
- Define dead-letter queue handling — what happens when a message in `rz-data-ingested-dlq` is not resolved
- Confirm whether `rz_processed` tables are materialized (scheduled query) or views (query-time compute)
- Confirm GCP project ID and region (europe-west1 recommended for GDPR proximity)
- Define alert/monitoring: Cloud Monitoring on the Pub/Sub subscription backlog and Cloud Function error rate

## Sources

- [Cloud Run jobs documentation — Google](https://cloud.google.com/run/docs/create-jobs)
- [Cloud Scheduler documentation — Google](https://cloud.google.com/scheduler/docs)
- [Pub/Sub documentation — Google](https://cloud.google.com/pubsub/docs)
- [BigQuery documentation — Google](https://cloud.google.com/bigquery/docs)
- [google-cloud-bigquery Python SDK](https://cloud.google.com/python/docs/reference/bigquery/latest)
