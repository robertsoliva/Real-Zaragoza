# Architecture — Data sources, pipeline, and BigQuery

> **Status:** living document, last updated 2026-07-24. Full medallion architecture live (raw → bronze → silver → gold). 20 leagues in scope (16 active + 4 backfilling). All BQ tables have table + column descriptions. WC 2026 complete and archived.

---

## Goal

Build a data foundation to:
- **Scout transfer targets** — compare players across 20 leagues against Zaragoza's squad and positional benchmarks
- **Analyse form and opponents** — team style profiles, Zaragoza match-by-match breakdown
- **Predict match outcomes** — model fixtures using historical stats + form (future)

---

## Data sources

| Source | What | Coverage | Method | Cadence |
|---|---|---|---|---|
| **SofaScore** | Matches, player stats, team stats, shot maps | 20 leagues + WC 2026 | curl_cffi Chrome TLS (local only — GCP IPs blocked) | 4 slots/day via launchd |
| **Transfermarkt** | Market values, contracts, positions, squad | 19 leagues (1RFEF excluded) + Zaragoza-only | httpx + BeautifulSoup | Quarterly (Cloud Run) |
| **Capology** | Gross wages | Top 5 EU leagues only (PL, La Liga, Bundesliga, Ligue 1, Serie A) | requests + BeautifulSoup | Monthly (Cloud Run) |

**Why SofaScore can't run on GCP:** Cloudflare blocks all GCP datacenter IPs even with Chrome TLS impersonation. The scraper must run locally via launchd.

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
| 2. Bundesliga | 35 | ⏳ backfilling | L2 |
| FIFA World Cup 2026 | 16 | ✅ complete (archived) | — |

Real Zaragoza team_id: **2815**. Run `pipeline/cloud-run/scrapers/seasons_lookup.py <tournament_id>` to discover season IDs.

---

## BigQuery architecture

GCP project: `real-zaragoza-500608` · Region: `europe-west1`

```
SofaScore (local) ──► raw.sofascore_*           ──► bronze (views)
                                                        │
Transfermarkt (GCP) ─► raw.transfermarkt_players       ▼
                    ─► raw.transfermarkt_squad    silver (deduped tables)
                                                        │
Capology (GCP) ──────► raw.capology_wages              ▼
                                                   gold (aggregated tables)
WC 2026 (local, done) ► wc_2026.sofascore_*  ──► bronze (via UNION ALL)
```

### Layer definitions

| Layer | Dataset | Type | Refresh |
|---|---|---|---|
| **Raw** | `raw`, `wc_2026` | Append-only partitioned tables | Written by scrapers |
| **Bronze** | `bronze` | Views (no storage) | Always live — no refresh needed |
| **Silver** | `silver` | Partitioned + clustered tables | Daily (`rz-refresh-layers` Cloud Run Job) |
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
| `agg_rz_squad_finances` | Zaragoza squad (TM latest) | Squad financial overview |
| `agg_league_player_benchmarks` | league × season × position (≥450 min) | Contextualise player stats |
| `agg_tm_player_valuations` | player × club × season × ingested_date | Market value history/trends |
| `agg_player_wage_benchmarks` | league × position_group | Wage P25/median/P75 (top 5 EU only) |

All tables have `OPTIONS(description=...)` with grain, source, and cluster/partition details. All columns are described.

---

## Cloud infrastructure

| Resource | Name | Purpose | Cadence |
|---|---|---|---|
| Cloud Run Job | `rz-refresh-layers` | Runs all bronze→silver→gold SQL | Daily 06:00 Madrid |
| Cloud Run Job | `rz-tm-scraper` | Transfermarkt multi-league scrape | Quarterly (1 Jan/Apr/Jul/Oct) |
| Cloud Run Job | `rz-capology-scraper` | Capology wage scrape (top 5 EU leagues) | Monthly (1st of month) |
| Cloud Scheduler | `rz-refresh-layers-daily` | Triggers `rz-refresh-layers` | Daily 06:00 Europe/Madrid |
| Cloud Scheduler | `rz-tm-scraper-quarterly` | Triggers `rz-tm-scraper` | 1 Jan/Apr/Jul/Oct 06:00 |
| Cloud Scheduler | `rz-capology-scraper-monthly` | Triggers `rz-capology-scraper` | 1st monthly 06:00 |
| Artifact Registry | `rz-images` | Docker images for all jobs | europe-west1 |
| Service account | `622526432554-compute@...` | Default compute SA (BQ write access) | — |

---

## SofaScore local cadence (launchd)

Since GCP IPs are blocked, all SofaScore scraping runs locally on macOS via launchd.

```
00:00 → run_next_from_queue.sh   (extraction slot 1)
06:00 → run_next_from_queue.sh   (extraction slot 2)
12:00 → run_next_from_queue.sh   (extraction slot 3)
18:00 → run_next_from_queue.sh   (extraction slot 4)
07:30 Tue → run_weekly_sofascore.sh  (incremental update for all active seasons)
```

Queue: `pipeline/cloud-run/schedules/sofascore_queue.txt` — one season per line. Each slot pops and runs one season. **Never run 2+ consecutive seasons — triggers 24h Cloudflare IP ban.**

**IP ban behaviour:** Even 2 consecutive seasons (~50 min) trips the ban. Symptoms: HTTP 403 `{"reason":"challenge"}`. Recovery: full 24h wait.

launchd plists in `pipeline/cloud-run/schedules/` — copies live in `~/Library/LaunchAgents/`.

---

## Pipeline code

```
pipeline/
  cloud-run/
    scrapers/
      scraper_sofascore.py              # SofaScore: 4 tables per run
      scraper_transfermarkt_leagues.py  # TM multi-league: raw.transfermarkt_players
      scraper_transfermarkt.py          # TM Zaragoza-only: raw.transfermarkt_squad
      scraper_capology.py               # Capology wages: raw.capology_wages
      seasons_lookup.py                 # Helper: discover SofaScore season IDs
    schedules/
      sofascore_queue.txt               # Backfill queue
      run_next_from_queue.sh            # Pops queue, runs 1 season
      run_weekly_sofascore.sh           # Incremental for active seasons
      run_daily_wc26.sh                 # WC 2026 daily (archived — tournament over)
      com.realzaragoza.sofascore-*.plist  # launchd job definitions
    refresh-layers/
      main.py                           # Ordered SQL execution (bronze→silver→gold)
      Dockerfile                        # Cloud Run image
      cloudbuild.yaml
    tm-scraper/                         # Cloud Run Job image for TM multi-league
    capology-scraper/                   # Cloud Run Job image for Capology
  sql/
    raw/                                # ALTER TABLE descriptions for raw tables
    wc_2026/                            # ALTER TABLE descriptions for WC tables
    bronze/                             # CREATE OR REPLACE VIEW statements
    silver/                             # CREATE OR REPLACE TABLE (dedup)
    gold/                               # CREATE OR REPLACE TABLE (aggregated)
                                        # Each model has a companion _descriptions.sql
```

---

## Known data issues

- **1RFEF 2024-25** — only ~100 matches loaded (expected ~380+). SofaScore may expose only playoff rounds for this season. Investigate before re-backfilling.
- **WC `league_name`** — rows from the initial WC backfill (before 2026-07-05) have `league_name = "tournament_16"`. Filter WC data by `tournament_id = "16"`, not `league_name`.
- **Capology coverage gap** — `raw.capology_wages` covers Premier League, La Liga, Bundesliga, Ligue 1, Serie A only. None of the SofaScore pipeline leagues are covered. `gold.agg_player_wage_benchmarks` is useful for top-league transfer targets only.

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
