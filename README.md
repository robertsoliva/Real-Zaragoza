# Real Zaragoza CF — Analysis

Data infrastructure and analysis project for Real Zaragoza CF. The goal is to build a foundation for:

- **Match prediction** — model outcomes for upcoming Zaragoza fixtures using historical form, opponent profiles, and expected-goals data
- **Signing evaluation** — compare transfer targets against current squad and division-wide benchmarks using per-match player stats and market valuations
- **Opponent scouting** — aggregate player and team stats across Segunda División and 1RFEF to identify patterns before they show up in results

---

## What's in this repo

```
wiki/              Reference knowledge — club history, finances, squad, technical architecture
pipeline/          Cloud Run scrapers and BigQuery table schemas
next-actions.md    Backlog of planned data work and analysis
```

**All persistent data lives in Google BigQuery** (`real-zaragoza-500608`). No raw files are committed here.

---

## Data

| Table | Source | Scope | Refresh |
|---|---|---|---|
| `rz_raw.transfermarkt_squad` | Transfermarkt | Squad, market values, contracts | Weekly |
| `rz_raw.sofascore_matches` | SofaScore | Match results by jornada (LaLiga2 + 1RFEF) | Weekly |
| `rz_raw.sofascore_player_match_stats` | SofaScore | Per-player stats per match (rating, goals, assists, passes, tackles, duels, xG, xA) | Weekly |
| `rz_raw.sofascore_shots` | SofaScore | Shot-level data with xG and pitch coordinates | Weekly |
| `rz_raw.sofascore_team_match_stats` | SofaScore | Team totals per match (possession, shots, passes, duels, big chances) | Weekly |

Tables are **append-only, partitioned by match date, clustered by jornada** — past seasons stay queryable alongside the current one.

Current coverage: **16 leagues** — LaLiga2, 1RFEF, Serie B, Ligue 2, Romanian SuperLiga, J1 League, Turkish Süper Lig, Norwegian Eliteserien, Austrian Bundesliga, Korean K League 1, Brasileirao Serie B, Mozzart Bet Superliga, MLS, Allsvenskan, Eerste Divisie, Moldovan Super Liga. WC 2026 in a separate dataset (`WC_26`). Backfill in progress; see `pipeline/cloud-run/schedules/sofascore_queue.txt`.

---

## Pipeline

```
launchd (macOS, local machine)
  ├── 00:00 / 06:00 / 12:00 / 18:00 → run_next_from_queue.sh → scraper_sofascore.py → rz_raw.sofascore_*
  ├── 09:00 daily → run_daily_wc26.sh (incremental, WC_26 dataset)
  └── 11:00 / 20:00 → run_refresh_processed.sh → rz_bronze / rz_silver / rz_gold
```

- **Backfill**: queue-driven via `sofascore_queue.txt`, 4 seasons/day, lock file prevents concurrent runs
- **Weekly incremental** (post-backfill): `INCREMENTAL=true` — scrapes last 14 days only (SofaScore blocks GCP IPs; runs locally)

Full technical reference: [`wiki/architecture.md`](wiki/architecture.md)

---

## Wiki

[`wiki/`](wiki/) is a living reference updated alongside the data:

| Page | Contents |
|---|---|
| [`architecture.md`](wiki/architecture.md) | Data sources, pipeline, BQ schemas, GCP setup, open items |
| [`current-situation.md`](wiki/current-situation.md) | Ownership, board, coaching staff — most volatile |
| [`squad.md`](wiki/squad.md) | 2026-27 squad rebuild: departures, signings, priorities |
| [`finances.md`](wiki/finances.md) | Debt history, wage caps, ownership eras |
| [`history.md`](wiki/history.md) | Founding, seasons, honours, stadium |
| [`records.md`](wiki/records.md) | All-time records, Pichichi winners, legendary players |
| [`academy.md`](wiki/academy.md) | Youth structure, graduates, current pipeline |
| [`identity-fan-culture.md`](wiki/identity-fan-culture.md) | Crest, colours, rivalry, fan culture |
