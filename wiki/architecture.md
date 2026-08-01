# Architecture — Data sources, pipeline, and BigQuery

> **Status:** living document, last updated 2026-08-01. Full medallion architecture live (raw → bronze → silver → gold) via dbt. 25 leagues in scope. GCS daily backup live. WC 2026 complete and archived. Dev/prod dbt split + GitHub Actions CI/CD added 2026-08-01 (see [Dev/prod split & CI/CD](#devprod-split--cicd)).

---

## Goal

Build a data foundation to:
- **Scout transfer targets** — compare players across 26 leagues against Zaragoza's squad and positional benchmarks
- **Analyse form and opponents** — team style profiles, Zaragoza match-by-match breakdown
- **Predict match outcomes** — model fixtures using historical stats + form (future)

---

## Data sources

| Source | What | Coverage | Method | Cadence |
|---|---|---|---|---|
| **SofaScore** | Matches, player stats, team stats, shot maps | 26 leagues + WC 2026 | curl_cffi Chrome TLS (local only — GCP IPs blocked) | 6 slots/day via launchd |
| **Transfermarkt** | Market values, contracts, positions, squad | 25 leagues (1RFEF excluded) | httpx + BeautifulSoup (**must run locally** — GCP IPs blocked) | Quarterly |
| **Capology** | Gross wages | Top 5 EU leagues (PL, La Liga, Bundesliga, Ligue 1, Serie A) | requests + BeautifulSoup | Quarterly (Cloud Run) |

**GCP IP blocking:** SofaScore and Transfermarkt both block GCP datacenter IPs via Cloudflare. Capology does not. SofaScore runs via local launchd. Transfermarkt's multi-league scraper (`rz-tm-scraper`) is configured as a Cloud Run Job but must be triggered manually from a local machine (see `pipeline/run_transfermarkt_leagues.sh`) until a workaround is found. Migrating SofaScore extraction to Cloud Run was investigated 2026-08-01 as a way to remove the local-machine dependency — confirmed SofaScore also blocks GCP datacenter IPs, same as TM. Not pursuing further; local-only extraction for both is a confirmed hard constraint, not a historical artifact.

---

## Active leagues

| League | Tournament ID | SofaScore Status | TM Code |
|---|---|---|---|
| LaLiga2 | 54 | ✅ loaded | ES2 |
| 1RFEF | 17073 | ✅ loaded | — (excluded from TM) |
| Serie B (Italy) | 53 | ✅ loaded | IT2 |
| Ligue 2 (France) | 182 | ✅ loaded | FR2 |
| Romanian SuperLiga | 152 | ✅ loaded | RO1 |
| J1 League (Japan) | 196 | ✅ loaded | JAP1 |
| Turkish Süper Lig | 52 | ✅ loaded | TR1 |
| Norwegian Eliteserien | 20 | ✅ loaded | NO1 |
| Austrian Bundesliga | 45 | ✅ loaded | A1 |
| Korean K League 1 | 410 | ✅ loaded | RSK1 |
| Brasileirao Serie B | 390 | ✅ loaded | BRA2 |
| Mozzart Bet Superliga | 210 | ✅ loaded | SER1 |
| MLS | 242 | ✅ loaded | MLS1 |
| Allsvenskan | 40 | ✅ loaded | SE1 |
| Eerste Divisie (NL 2nd) | 131 | ✅ loaded | NL2 |
| Moldovan Super Liga | 685 | ✅ loaded | MO1N |
| Eredivisie | 37 | ⏳ backfilling | NL1 |
| Belgian Pro League | 38 | ⏳ backfilling | BE1 |
| Liga Portugal | 238 | ⏳ backfilling | PO1 |
| Bundesliga (1st div) | 35 | ⏳ backfilling | L1 |
| 2. Bundesliga | 44 | ⏳ backfilling | L2 |
| Premier League | 17 | ⏳ backfilling | GB1 |
| La Liga | 8 | ⏳ backfilling | ES1 |
| Serie A | 23 | ⏳ backfilling | IT1 |
| Ligue 1 | 34 | ⏳ backfilling | FR1 |
| FIFA World Cup 2026 | 16 | ✅ complete (archived) | — |

Real Zaragoza team_id: **2815**. Run `pipeline/cloud-run/scrapers/seasons_lookup.py <tournament_id>` to discover season IDs.

---

## BigQuery architecture

GCP project: `real-zaragoza-500608` · Region: `europe-west1`

```
SofaScore (local) ──► raw.sofascore_*           ──► bronze (views)
                                                        │
Transfermarkt (local) ─► raw.transfermarkt_players     ▼
                                                 silver (deduped tables)
                                                        │
Capology (GCP) ──────► raw.capology_wages              ▼
                                                   gold (aggregated tables + dims)
WC 2026 (local, done) ► wc_2026.sofascore_*  ──► bronze (via UNION ALL)
```

### Layer definitions

| Layer | Dataset | Type | Refresh |
|---|---|---|---|
| **Raw** | `raw`, `wc_2026` | Append-only partitioned tables | Written by scrapers |
| **Bronze** | `bronze` | Views (no storage) | Always live — no refresh needed |
| **Silver** | `silver` | Partitioned + clustered tables | Daily (`rz-dbt-refresh`) |
| **Gold** | `gold` | Clustered tables (some partitioned) | Daily (same job, after silver) |

**Always query `silver` or `gold`** — never `raw` directly (duplicates, no dedup).

### Gold tables

| Table | Grain | Primary use |
|---|---|---|
| `fct_player_season_stats` | player × team × league × season | Scouting, player trends |
| `fct_team_season_stats` | team × league × season | Team style comparison |
| `fct_rz_matches` | match (Zaragoza only) | Form analysis, W/D/L |
| `agg_player_market_values` | player × club × season (TM latest) | Market value per player |
| `agg_scouting_player_season` | player × league × season (stats + TM joined) | **Main scouting table** |
| `agg_rz_squad_finances` | Zaragoza squad (TM quarterly) | Squad financial overview |
| `agg_league_player_benchmarks` | league × season × position (≥450 min) | Contextualise player stats |
| `agg_tm_player_valuations` | player × club × season × ingested_date | Market value history/trends |
| `agg_player_wage_benchmarks` | league × position_group | Wage P25/median/P75 (top 5 EU only) |
| `dim_league` | tournament_id (insert-only) | League metadata + country |
| `dim_team` | team_id (insert-only) | Team name lookup |
| `dim_player` | player_id (insert-only) | Fixed player attributes: position, nationality, foot, height |

All tables have `OPTIONS(description=...)` and column-level descriptions (via dbt `schema.yml` + `persist_docs`).

---

## dbt pipeline

dbt models live in `pipeline/dbt/`. The pipeline runs as Cloud Run Job `rz-dbt-refresh`.

- **Models:** `pipeline/dbt/models/{bronze,silver,gold}/` — 28 models total (includes `agg_player_profiles`, tagged `player_clustering`, excluded from the daily run)
- **Schema/docs:** `pipeline/dbt/models/{bronze,silver,gold}/schema.yml`
- **Naming:** layer-prefixed filenames (`silver_matches.sql`) with `alias` config → clean BQ table names (`silver.matches`)
- **Dim tables:** insert-only via incremental merge strategy; capture fixed attributes only (position, nationality, foot, height — not variable like market value)
- **Macro:** `generate_schema_name.sql` routes each model to its correct dataset — `bronze`/`silver`/`gold` when `target: prod`, `dev_bronze`/`dev_silver`/`dev_gold` for any other target (see below)
- **Seeds:** `pipeline/dbt/seeds/` — `club_name_aliases.csv` (SofaScore↔TM club name/ID bridge) and `player_id_map.csv` (SofaScore↔TM player identity crosswalk, built 2026-08-01, **not currently wired into any model** — see [Known data issues](#known-data-issues))
- **Concurrency:** `rz-dbt-refresh` is triggered by 2 independent schedulers (Cloud Scheduler + launchd ×2, see below) with no coordination between them. `pipeline/cloud-run/dbt-refresh/run_with_lock.py` (the container's ENTRYPOINT, added 2026-08-01) wraps `dbt deps/seed/run` with a BigQuery-backed mutual-exclusion lock (`ops.pipeline_locks`) so overlapping triggers can't run concurrent `dbt run`s against the same tables. Fails open (runs dbt anyway) if the lock check itself errors — a lock bug should never be able to silently stop the pipeline from refreshing.

---

## Dev/prod split & CI/CD

Added 2026-08-01, motivated by a live incident: fixing a `league_name` mislabeling bug required deploying straight to production BigQuery tables with no review gate.

**BigQuery:** `dev_bronze`/`dev_silver`/`dev_gold` datasets mirror `bronze`/`silver`/`gold`, built from the same `raw`/`wc_2026` sources (no duplicate scraping). `profiles.yml` defaults to `target: dev` — a bare local `dbt run` can never touch production by accident. The deployed `rz-dbt-refresh` container explicitly passes `--target prod` in `run_with_lock.py`, so its behavior is unchanged.

**GitHub Actions** (`.github/workflows/`):
- `dbt-ci.yml` — runs `dbt build --target dev` (deps → seed → run → test) on every PR touching `pipeline/dbt/**`. This is the review gate. On its first real run (2026-08-01) it caught a genuine bug: `fct_player_season_stats` grouped by `player_name` instead of aggregating it, splitting one player's season stats across two rows because SofaScore had scraped two spelling variants of their name.
- `dbt-deploy-prod.yml` — `workflow_dispatch`-only (never fires on push/merge), requires typing `deploy` to confirm. Rebuilds the `rz-dbt-refresh` Cloud Run image (same `gcloud builds submit` command previously run by hand) and executes it once against prod. **The only path that's supposed to push dbt code changes to production.** The regular 3x/day scheduled refreshes (below) re-run whatever code is already in the deployed image — they don't deploy new code, only fresh data.

**Auth:** Workload Identity Federation, not a stored service-account key — GitHub's OIDC token is exchanged for short-lived GCP credentials at workflow-run time, scoped to this exact repo. One-time setup: `pipeline/scripts/setup_github_actions_wif.sh` (creates a dedicated `github-actions-dbt` service account, least-privilege: `bigquery.dataViewer` on `raw`/`wc_2026`, `bigquery.dataEditor` on `dev_*` only — **cannot write to prod bronze/silver/gold directly**, can only ask Cloud Build/Cloud Run to run the existing `rz-dbt-refresh` job, which writes to prod under its own separate identity).

---

## Cloud infrastructure

| Resource | Name | Purpose | Cadence |
|---|---|---|---|
| Cloud Run Job | `rz-dbt-refresh` | dbt run (all bronze → silver → gold), lock-wrapped | Daily 06:00 Madrid + launchd 11:00/20:00 |
| Cloud Run Job | `rz-tm-scraper` | Transfermarkt multi-league scrape | Quarterly (1 Jan/Apr/Jul/Oct) — **must be triggered from local machine** |
| Cloud Run Job | `rz-capology-scraper` | Capology wage scrape (top 5 EU leagues) | Quarterly (1 Jan/Apr/Jul/Oct 06:00) |
| Cloud Scheduler | `rz-dbt-refresh-daily` | Triggers `rz-dbt-refresh` | Daily 06:00 Europe/Madrid |
| Cloud Scheduler | `rz-tm-scraper-quarterly` | Triggers `rz-tm-scraper` | 1 Jan/Apr/Jul/Oct 06:00 (run from local machine instead) |
| Cloud Scheduler | `rz-capology-scraper-quarterly` | Triggers `rz-capology-scraper` | 1 Jan/Apr/Jul/Oct 06:00 |
| GCS Bucket | `rz-raw-backups` | Daily Parquet snapshot of all raw tables (incl. TM/Capology/wage predictions) | After each SofaScore extraction |
| Artifact Registry | `rz-images` | Docker images for all jobs | europe-west1 |
| BQ dataset | `ops` | Pipeline operational metadata — currently just `pipeline_locks` (concurrency lock) | Written by `run_with_lock.py` |
| BQ datasets | `dev_bronze`/`dev_silver`/`dev_gold` | dbt CI target — never read by production code | Written by `dbt-ci.yml` on every PR |
| GitHub Actions | `dbt-ci.yml`, `dbt-deploy-prod.yml` | dev CI on PR; manual-only prod deploy | See above |
| Service account | `622526432554-compute@...` | Default compute SA (BQ write access) | — |
| Service account | `github-actions-dbt@...` | GitHub Actions WIF identity — dev read/write only, no direct prod BQ access | — |

---

## Local extraction cadence (launchd)

Since GCP IPs are blocked, all SofaScore scraping runs locally on macOS via launchd.

```
00:00 → run_next_from_queue.sh   (extraction slot 1)
04:00 → run_next_from_queue.sh   (extraction slot 2)
08:00 → run_next_from_queue.sh   (extraction slot 3)
11:00 → run_refresh_processed.sh (triggers rz-dbt-refresh)
12:00 → run_next_from_queue.sh   (extraction slot 4)
16:00 → run_next_from_queue.sh   (extraction slot 5)
20:00 → run_next_from_queue.sh   (extraction slot 6)
20:00 → run_refresh_processed.sh (triggers rz-dbt-refresh)
07:30 Tue → run_weekly_sofascore.sh  (incremental for all active seasons)
```

Each extraction slot also triggers `backup_raw_to_gcs.sh` to snapshot raw BQ tables to GCS.

Queue: `pipeline/cloud-run/schedules/sofascore_queue.txt` — one season per line. Each slot pops and runs one season. **Never run 2+ consecutive seasons — triggers 24h Cloudflare IP ban.**

**IP ban behaviour:** Even 2 consecutive seasons (~50 min) trips the ban. Symptoms: HTTP 403 `{"reason":"challenge"}`. Recovery: full 24h wait.

launchd plists in `pipeline/cloud-run/schedules/` — copies live in `~/Library/LaunchAgents/`.

---

## GCS backup

All raw BQ tables are exported to `gs://rz-raw-backups` (GCP project `real-zaragoza-500608`, region `europe-west1`) after every SofaScore extraction.

```
gs://rz-raw-backups/
  YYYY-MM-DD/
    raw/
      sofascore_matches/*.parquet
      sofascore_player_match_stats/*.parquet
      sofascore_shots/*.parquet
      sofascore_team_match_stats/*.parquet
      transfermarkt_players/*.parquet
      capology_wages/*.parquet
    wc_2026/
      sofascore_matches/*.parquet
      sofascore_player_match_stats/*.parquet
      sofascore_shots/*.parquet
      sofascore_team_match_stats/*.parquet
```

Six extractions per day all overwrite the same date path — one snapshot per calendar day. To restore a table: `bq load --source_format=PARQUET PROJECT:DATASET.TABLE 'gs://rz-raw-backups/DATE/dataset/table/*.parquet'`.

---

## Pipeline code

```
.github/
  workflows/
    dbt-ci.yml                          # dbt build --target dev on every PR
    dbt-deploy-prod.yml                 # workflow_dispatch-only prod deploy
pipeline/
  cloud-run/
    scrapers/
      scraper_sofascore.py              # SofaScore: 4 tables per run
      scraper_transfermarkt_leagues.py  # TM multi-league: raw.transfermarkt_players
      scraper_transfermarkt.py          # TM Zaragoza-only (orphan — job deleted, file preserved)
      scraper_capology.py               # Capology wages: raw.capology_wages
      seasons_lookup.py                 # Helper: discover SofaScore season IDs
    schedules/
      sofascore_queue.txt               # Backfill queue
      run_next_from_queue.sh            # Pops queue, runs 1 season, calls GCS backup
      run_weekly_sofascore.sh           # Incremental for active seasons (Tue 07:30)
      run_refresh_processed.sh          # Triggers rz-dbt-refresh Cloud Run Job
      backup_raw_to_gcs.sh              # Exports raw tables to gs://rz-raw-backups/
      send_daily_summary.py             # Daily digest email + TM-match/freshness alerts
      tm_match_baseline.json            # Per-league TM-match-rate baseline for regression alerts
      com.realzaragoza.sofascore-*.plist  # launchd job definitions (6 daily slots)
      com.realzaragoza.refresh-*.plist    # launchd refresh triggers (11:00 + 20:00)
      run_daily_wc26.sh                 # WC 2026 daily scrape (archived)
    dbt-refresh/                        # Cloud Run Job image
      Dockerfile / cloudbuild.yaml
      run_with_lock.py                  # ENTRYPOINT: BQ-locked dbt deps/seed/run --target prod
    tm-scraper/                         # Cloud Run Job image: TM multi-league
    capology-scraper/                   # Cloud Run Job image: Capology
    wage-predictor/                     # Cloud Run Job image: BQML wage regression + predictions
    player-clustering/                  # Manual-retrain scripts: k-means archetype models
    docker/                             # Historical Docker configs (SofaScore only; TM Zaragoza-only job deleted)
    archive/                            # Historical one-off backfill scripts
  dbt/                                  # dbt project
    dbt_project.yml / profiles.yml      # target: dev by default; prod requires --target prod
    macros/generate_schema_name.sql     # Routes models to bronze/silver/gold or dev_*
    models/
      sources.yml                       # raw + wc_2026 source declarations
      bronze/   (8 models — views, alias to bronze.*)
      silver/   (8 models — deduped tables, alias to silver.*)
      gold/     (13 models — aggregated tables + dims, incl. agg_player_profiles)
    seeds/
      club_name_aliases.csv             # SofaScore<->TM club name/ID bridge
      player_id_map.csv                 # SofaScore<->TM player crosswalk (not wired in, see Known data issues)
  scripts/                              # One-off/maintenance scripts (not scheduled)
    build_team_id_map.py                # Populates club_name_aliases.csv ID columns
    build_player_id_map.py              # Builds player_id_map.csv
    setup_github_actions_wif.sh         # One-time GCP IAM setup for GitHub Actions
  bq-schemas/                           # BQ JSON schemas for raw tables
  run_transfermarkt_leagues.sh          # One-shot TM multi-league runner
```

---

## Known data issues

- **1RFEF 2024-25** — only ~100 matches loaded (expected ~380+). SofaScore may expose only playoff rounds for this season. Investigate before re-backfilling.
- **WC `league_name`** — rows from the initial WC backfill (before 2026-07-05) have `league_name = "tournament_16"`. Filter WC data by `tournament_id = "16"`, not `league_name`.
- **Capology coverage gap** — `raw.capology_wages` covers Premier League, La Liga, Bundesliga, Ligue 1, Serie A only. None of the SofaScore pipeline leagues are covered. `gold.agg_player_wage_benchmarks` is useful for top-league transfer targets only.
- **`league_name` mislabeling for tournament_id 17/8/23/34 — fixed 2026-08-01.** Same class of bug as the WC one above: the scraper's `LEAGUE_NAMES` dict and the bronze CASE patches only covered tournament_id 16/35/44, so Premier League (17)/La Liga (8)/Serie A (23)/Ligue 1 (34) fell through to `tournament_{id}`. Fixed in the scraper and all 4 bronze models; verified clean in `dev_silver.matches` after rebuild.
- **`fct_player_season_stats` duplicate rows for players with inconsistent scraped name spelling — fixed 2026-08-01.** The model grouped by `player_name` instead of aggregating it (`ANY_VALUE`, matching `primary_position`'s existing pattern), so a `player_id` scraped under two name spellings (e.g. an accent dropped in one match) split into two season rows instead of one. Found by `dbt test` running against the new dev target for the first time — the prod Cloud Run job has never run `dbt test`, only `dbt run`.
- **SofaScore↔TM identity crosswalk — investigated 2026-08-01, shelved.** `pipeline/scripts/build_player_id_map.py` builds a static `sofascore_player_id ↔ tm_player_id` map (output: `pipeline/dbt/seeds/player_id_map.csv`), but isn't wired into `agg_scouting_player_season` or `silver_bqml_wages`. Measured: the trusted match tier only rescues 5.1% more scouting-relevant players than the existing name+club join, with zero disagreements found (no evidence the existing join is silently wrong, just incomplete). 68.6% of the remaining unmatched players is a TM data-coverage gap (club/player simply not in TM's quarterly snapshot), not a matching-algorithm problem — the higher-leverage fix would be TM scrape completeness/cadence, not further identity-matching work. Full methodology in git history for commit `58fedd5`.

---

## Agent ecosystem

| Agent | Role | AGENT.md |
|---|---|---|
| `data-lead` | Vision, roadmap, governance | `.claude/agents/data-lead/AGENT.md` |
| `data-engineer` | SQL, BQ schemas, pipeline code | `.claude/agents/data-engineer/AGENT.md` |
| `data-scout` | Scouting reports, acquisition fit | `.claude/agents/data-scout/AGENT.md` |
| `match-analyst` | Form, match breakdowns, benchmarks | `.claude/agents/match-analyst/AGENT.md` |

## Sources

- [SofaScore](https://www.sofascore.com/)
- [Transfermarkt](https://www.transfermarkt.es/real-zaragoza/kader/verein/142/plus/1)
- [Capology](https://www.capology.com/)
- [GCP Cloud Run Jobs](https://cloud.google.com/run/docs/create-jobs)
- [BigQuery partitioned tables](https://cloud.google.com/bigquery/docs/partitioned-tables)
