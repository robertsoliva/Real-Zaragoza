# Data Pipeline — Ingestion architecture and BigQuery schema

> **Status:** living document, last updated 2026-06-26. Transfermarkt scraper built and verified (32 players, all fields confirmed against live page). BQ historical strategy decided. SofaScore scraper and GCP deployment pending.

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

- **SofaScore scraper strategy** — unofficial internal API (reverse-engineered endpoints); rate-limit sensitive, needs investigation
- **DLQ handling** — define what happens when a message in `rz-data-ingested-dlq` is not resolved (manual replay vs. auto-retry limit)
- **`rz_processed` materialisation** — views are the plan; confirm whether query-time cost warrants materialised tables once data volume grows
- **GCP project ID and region** — europe-west1 recommended for GDPR proximity; confirm with robertsoliva before creating resources
- **Monitoring** — Cloud Monitoring alerts on Pub/Sub subscription backlog and Cloud Function error rate

## Sources

- [Cloud Run jobs documentation — Google](https://cloud.google.com/run/docs/create-jobs)
- [Cloud Scheduler documentation — Google](https://cloud.google.com/scheduler/docs)
- [Pub/Sub documentation — Google](https://cloud.google.com/pubsub/docs)
- [BigQuery documentation — Google](https://cloud.google.com/bigquery/docs)
- [google-cloud-bigquery Python SDK](https://cloud.google.com/python/docs/reference/bigquery/latest)
