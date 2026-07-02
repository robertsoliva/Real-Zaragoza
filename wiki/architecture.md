# Architecture — Data sources, pipeline, and BigQuery

> **Status:** living document, last updated 2026-07-01. Transfermarkt + SofaScore pipelines live. SofaScore now covers 6 leagues. Full 12-season backfill running locally. Agent ecosystem (data-lead, data-engineer, data-scout, match-analyst) in place.

## Goal

Build a data foundation to:
- **Predict match outcomes** — model Zaragoza fixtures using historical and live form data
- **Evaluate signings** — compare targets against current squad and league-wide benchmarks
- **Scout opponents** — aggregate player and team stats across 6 leagues (LaLiga2, 1RFEF, Serie B, Ligue 2, Romanian SuperLiga, J1 League)

---

## Data sources

| Source | What | Leagues | Method | Status |
|---|---|---|---|---|
| **Transfermarkt** | Squad, market values, contracts | All (Zaragoza only) | httpx + BeautifulSoup | Live, weekly |
| **SofaScore** | Match results, player stats, team stats, shot maps | LaLiga2, 1RFEF, Serie B, Ligue 2, Romanian SuperLiga, J1 League | curl_cffi (Chrome TLS impersonation) | Live locally; Cloud Run blocked by Cloudflare |

**Why SofaScore over FotMob:** FotMob provides only match results (`lower` coverage) for 1RFEF with no player stats. SofaScore has full player and team stats for both LaLiga2 and 1RFEF, and was extended to 4 additional leagues on 2026-07-01 for scouting context.

---

## SofaScore IDs

| League | Tournament ID | 2024-25 Season ID | 2025-26 Season ID | Notes |
|---|---|---|---|---|
| LaLiga2 | 54 | 62048 | 77558 | |
| 1RFEF | 17073 | 64430 | 77727 | |
| Serie B (Italy) | 53 | 63812 | 79502 | |
| Ligue 2 (France) | 182 | 61737 | 77357 | 2026-27 = 96109 |
| Romanian SuperLiga | 152 | 62837 | 77312 | 2026-27 = 97124 |
| J1 League (Japan) | 196 | 2025 = 69871 | 2026 = 87931 | Calendar-year seasons |

Real Zaragoza team ID: **2815**. Run `python seasons_lookup.py <tournament_id>` to discover future season IDs.

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

All 12 seasons backfilled via `backfill_all.sh` (run 2026-07-01). Use the same script for future re-backfills. For a single league/season:
```bash
GCP_PROJECT_ID=real-zaragoza-500608 TOURNAMENT_ID=54 SEASON_ID=77558 python3 scraper_sofascore.py
```

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
| `tournament_id` | STRING | 54=LaLiga2, 17073=1RFEF, 53=Serie B, 182=Ligue 2, 152=Romanian SuperLiga, 196=J1 |
| `season_id` | STRING | e.g. 62048, 77558 |
| `league_name` | STRING | Human-readable: LaLiga2, 1RFEF, Serie B, Ligue 2, Romanian SuperLiga, J1 League |
| `home_team_id` / `away_team_id` | STRING | SofaScore team IDs |
| `home_team_name` / `away_team_name` | STRING | |
| `home_score` / `away_score` | INT64 | |
| `status` | STRING | finished / notstarted / inprogress |
| `ingested_date` / `ingested_at` | DATE / TIMESTAMP | Audit |

### `rz_raw.sofascore_player_match_stats`
Partition: `match_date`. Clustered by: `match_round`, `team_id`.  
One row per player per match (starters + substitutes). Rows with all-null stats are skipped at ingest (SofaScore didn't process the match yet, or league lacks detail).

Context columns on every row: `tournament_id`, `season_id`, `league_name` (no join to matches needed).

Stat columns are tagged in BQ column descriptions with a category: **[Attacking]** `goals`, `goal_assists`, `total_shots`, `shots_on_target`, `expected_goals`, `expected_assists` — **[Passing]** `total_passes`, `accurate_passes`, `total_long_balls`, `accurate_long_balls`, `total_crosses`, `accurate_crosses`, `key_passes` — **[Defending]** `aerial_won`, `aerial_lost`, `duel_won`, `duel_lost`, `challenge_lost`, `total_tackle`, `won_tackle`, `interceptions`, `total_clearance`, `ball_recovery`, `saves` — **[Physical]** `minutes_played`, `touches`, `dispossessed`, `was_fouled`, `fouls`, `possession_lost`, `unsuccessful_touch`, `yellow_cards`, `red_cards`.

Full schema: [`pipeline/bq-schemas/sofascore_player_match_stats.json`](../pipeline/bq-schemas/sofascore_player_match_stats.json)

### `rz_raw.sofascore_shots`
Partition: `match_date`. Clustered by: `match_round`.  
One row per shot attempt. Context columns: `tournament_id`, `season_id`, `league_name`.

Key fields: `shot_id`, `player_id`, `player_name`, `is_home`, `minute`, `x`/`y` (shot origin), `goal_mouth_x`/`y`/`z`, `goal_mouth_location`, `block_x`/`y`, `body_part`, `shot_type` (goal/save/miss/blocked), `situation`, `xg` (null for lower leagues). All coordinates tagged **[Attacking]** except block coords (**[Defending]**).

Full schema: [`pipeline/bq-schemas/sofascore_shots.json`](../pipeline/bq-schemas/sofascore_shots.json)

### `rz_raw.sofascore_team_match_stats`
Partition: `match_date`. Clustered by: `match_round`, `team_id`.  
Two rows per match (home + away). Context columns: `tournament_id`, `season_id`, `league_name`.

Stat columns by category — **[Attacking]** `total_shots`, `shots_on_target/off_target/blocked/woodwork`, `shots_inside/outside_box`, `big_chances*`, `corners`, `offsides`, `touches_in_opp_box` — **[Passing]** `total/accurate_passes`, `long_balls`, `crosses`, `final_third_*`, `final_third_entries` — **[Defending]** `total/won_tackles`, `interceptions`, `clearances`, `ball_recoveries`, `errors_leading_to_shot`, `goalkeeper_saves`, `ground/aerial_duels_*` — **[Physical]** `possession_pct`, `fouls`, `yellow/red_cards`, `dribbles_*`, `dispossessed`.

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
    scraper_sofascore.py         # SofaScore scraper (backfill + incremental, 6 leagues)
    seasons_lookup.py            # Helper: list all season IDs for any tournament
    backfill_all.sh              # One-shot: 12 seasons × 6 leagues (run after table truncate)
    run_weekly_sofascore.sh      # Weekly incremental: all 6 active seasons, INCREMENTAL=true
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

## Weekly local cron (macOS launchd)

Since SofaScore blocks GCP IPs, the weekly incremental run must execute on a local machine. A launchd agent handles this automatically — it fires every Tuesday at 07:30, runs the scraper for both active seasons with `INCREMENTAL=true`, and writes directly to BigQuery via ADC.

**Files:**

| File | Purpose |
|---|---|
| `pipeline/cloud-run/run_weekly_sofascore.sh` | Wrapper: sets env vars, runs scraper for each season, logs to `/tmp/sofascore_weekly_YYYYMMDD.log` |
| `~/Library/LaunchAgents/com.realzaragoza.sofascore-weekly.plist` | launchd job definition — **not committed to git** (system folder) |

**One-time setup on a new machine:**

```bash
# 1. Authenticate to GCP
gcloud auth application-default login

# 2. Copy the plist to the LaunchAgents folder
cp pipeline/cloud-run/com.realzaragoza.sofascore-weekly.plist \
   ~/Library/LaunchAgents/

# 3. Register it with launchd
launchctl load ~/Library/LaunchAgents/com.realzaragoza.sofascore-weekly.plist

# 4. Verify it's registered
launchctl list | grep realzaragoza
```

**To trigger manually (e.g. after a missed Tuesday):**
```bash
launchctl start com.realzaragoza.sofascore-weekly
# or run the wrapper directly:
bash pipeline/cloud-run/run_weekly_sofascore.sh
```

**Season update (start of each season):** edit `run_weekly_sofascore.sh` and update `SEASON_ID` for each tournament.

**Rate limiting:** `REQUEST_DELAY=3.0s` between API calls, `ROUND_DELAY=8.0s` between rounds. Writes flush per round so a crash only loses the current round.

**IP ban behaviour (confirmed 2026-07-01):** Scraping ~3 consecutive full seasons (~3 hours of continuous requests) triggers a **24-hour Cloudflare IP ban** — not a short cooldown. The scraper returns `Could not fetch rounds` immediately; a plain curl shows HTTP 403. Recovery: wait the full 24 hours. Prevention: `backfill_retry.sh` inserts a **15-minute pause between each league group** (`LEAGUE_PAUSE=900`). Do not run more than 2–3 consecutive full seasons without a break.

---

## Agent ecosystem

Four analytical agents live in `.claude/agents/`. Each reads its own `AGENT.md` at the start of every session to load context and constraints.

| Agent | Role | Cannot |
|---|---|---|
| `data-lead` | Vision, roadmap, governance, documentation | Write SQL, run pipelines |
| `data-engineer` | SQL, dbt, BQ schemas, pipeline code | Update wiki, set strategy |
| `data-scout` | Player profiles, acquisition fit analysis | Match/team analysis |
| `match-analyst` | Zaragoza form, match breakdowns, league benchmarks | Transfer recommendations |

---

## World Cup 2026 (`WC_26`)

BQ dataset `WC_26` (europe-west1) created 2026-07-01 for FIFA World Cup 2026 data (tournament runs June 11 – July 19 2026). Same 4-table schema as `rz_raw`; updated daily at 09:00 during the tournament.

| Resource | Detail |
|---|---|
| BQ dataset | `real-zaragoza-500608:WC_26` |
| Tables | `sofascore_matches`, `sofascore_player_match_stats`, `sofascore_team_match_stats`, `sofascore_shots` — identical schema to `rz_raw` |
| Daily script | `pipeline/cloud-run/run_daily_wc26.sh` — runs `INCREMENTAL=true, BQ_DATASET=WC_26` |
| launchd plist | `pipeline/cloud-run/com.realzaragoza.wc26-daily.plist` — fires 09:00 daily |
| WC tournament ID | **TBD** — run `python3 seasons_lookup.py 17` once IP ban clears |
| WC season ID | **TBD** — same lookup |

`scraper_sofascore.py` now accepts `BQ_DATASET` env var (default `rz_raw`); set `BQ_DATASET=WC_26` to write to the WC dataset. Historical backfill from June 11 still pending IP ban lift.

---

## Open items

- **League retry backfill** — 9/12 seasons failed 2026-07-01 due to 24-hour IP ban (triggered by 3 consecutive full seasons). `backfill_retry.sh` is ready with 15-min inter-league pauses. Will auto-launch when IP clears (~13:30 on 2026-07-02). Order: Serie B → Ligue 2 → Romanian SuperLiga → J1 → 1RFEF last.
- **WC_26 backfill + IDs** — find WC 2026 tournament/season IDs via `seasons_lookup.py`, patch `run_daily_wc26.sh`, run full historical backfill (June 11 → today), then register launchd plist for daily 09:00.
- **1RFEF 2024-25 anomaly** — only 100 matches loaded (expected ~380+). May be SofaScore exposing only playoff rounds via the rounds API. Investigate structure before re-backfilling.
- **Weekly automation** — `rz-weekly-sofascore` scheduler is paused (GCP IPs blocked). `run_weekly_sofascore.sh` covers all 6 leagues; needs launchd plist update to reflect new leagues.
- **1RFEF 2026-27** — season ID not yet available on SofaScore; check ~July 2026. Add to `run_weekly_sofascore.sh` when available.
- **Dedup view** — `rz_processed.match_dedup` on `(match_id)` keeping latest `ingested_at`.
- **`rz_processed.season_results`** — W/D/L, GD, points per team per season from `sofascore_matches` once backfills confirmed.
- **Bronze/silver/gold layers** — dbt models on top of `rz_raw`; not yet started.

## Sources

- [SofaScore — sofascore.com](https://www.sofascore.com/es-la/football/tournament/spain/laliga-2/54)
- [Transfermarkt — verein/142/plus/1](https://www.transfermarkt.es/real-zaragoza/kader/verein/142/plus/1)
- [Cloud Run jobs documentation](https://cloud.google.com/run/docs/create-jobs)
- [BigQuery partitioned tables](https://cloud.google.com/bigquery/docs/partitioned-tables)
