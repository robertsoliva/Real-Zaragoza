# Real Zaragoza CF — Analysis

Data infrastructure and analysis project for Real Zaragoza CF. The goal is to build a foundation for:

- **Signing evaluation** — compare transfer targets against current squad and division-wide benchmarks using per-match player stats and market valuations
- **Match prediction** — model outcomes for upcoming Zaragoza fixtures using historical form, opponent profiles, and xG data
- **Opponent scouting** — aggregate player and team stats across 26 leagues to identify patterns before they show up in results

---

## What's in this repo

```
wiki/              Reference knowledge — club history, finances, squad, architecture
pipeline/          Scrapers, BigQuery SQL, launchd schedules, Cloud Run Jobs
next-actions.md    Backlog of planned data work and analysis
```

**All persistent data lives in Google BigQuery** (`real-zaragoza-500608`). No raw files are committed.

---

## Data platform

Medallion architecture: `raw` → `bronze` (views) → `silver` (deduped tables) → `gold` (aggregated tables).

| Source | Coverage | Method | Cadence |
|---|---|---|---|
| **SofaScore** | 26 leagues + WC 2026 | curl_cffi Chrome TLS (local only) | 6 slots/day via launchd |
| **Transfermarkt** | 25 leagues (1RFEF excluded) + Zaragoza squad | httpx + BeautifulSoup | Quarterly (Cloud Run) |
| **Capology** | Top 5 EU leagues (wages) | requests + BeautifulSoup | Monthly (Cloud Run) |

**Active leagues (16):** LaLiga2, 1RFEF, Serie B, Ligue 2, Romanian SuperLiga, J1 League, Turkish Süper Lig, Norwegian Eliteserien, Austrian Bundesliga, Korean K League 1, Brasileirao Serie B, Mozzart Bet Superliga, MLS, Allsvenskan, Eerste Divisie, Moldovan Super Liga.

**Backfilling (10):** Eredivisie, Belgian Pro League, Liga Portugal, Bundesliga, 2. Bundesliga, Premier League, La Liga, Serie A, Ligue 1, + WC 2026 (complete, archived).

Full technical reference: [`wiki/architecture.md`](wiki/architecture.md)

---

## Pipeline

```
launchd (macOS, local)
  ├── 00:00 / 04:00 / 08:00 / 12:00 / 16:00 / 20:00 → run_next_from_queue.sh → raw.sofascore_*
  └── 07:30 Tue → run_weekly_sofascore.sh (incremental, all 26 active seasons)

Cloud Run Jobs (GCP, europe-west1)
  ├── rz-dbt-refresh     → bronze/silver/gold (dbt)  (daily 06:00 + launchd 11:00/20:00, lock-guarded)
  ├── rz-tm-scraper      → raw.transfermarkt_*       (quarterly 1 Jan/Apr/Jul/Oct)
  └── rz-capology-scraper → raw.capology_wages       (quarterly 1 Jan/Apr/Jul/Oct)

launchd (macOS, local)
  └── 22:00 daily → send_daily_summary.py → email digest to rsolivamachin@gmail.com
```

Backfill queue: `pipeline/cloud-run/schedules/sofascore_queue.txt` — 1 season per slot, lock file prevents concurrent runs. **Never run 2+ consecutive seasons manually — triggers 24h Cloudflare IP ban.**

dbt changes go through CI/CD, not straight to prod: PRs run `dbt build` against dev-only BigQuery datasets (GitHub Actions), and only a manually-triggered workflow deploys to production. Detail: [`wiki/architecture.md`](wiki/architecture.md#devprod-split--cicd).

---

## Wiki

[`wiki/`](wiki/) is a living reference updated alongside the data:

| Page | Contents |
|---|---|
| [`architecture.md`](wiki/architecture.md) | Data sources, pipeline, BQ schemas, known issues |
| [`squad.md`](wiki/squad.md) | 2026-27 squad rebuild: departures, signings, priorities |
| [`current-situation.md`](wiki/current-situation.md) | Ownership, board, coaching staff |
| [`finances.md`](wiki/finances.md) | Debt history, wage caps, ownership eras |
| [`history.md`](wiki/history.md) | Founding, seasons, honours, stadium |
| [`records.md`](wiki/records.md) | All-time records, Pichichi winners, legendary players |
| [`academy.md`](wiki/academy.md) | Youth structure, graduates, current pipeline |
| [`identity-fan-culture.md`](wiki/identity-fan-culture.md) | Crest, colours, rivalry, fan culture |
