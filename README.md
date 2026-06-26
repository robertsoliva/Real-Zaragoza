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
| `rz_raw.fotmob_matches` | FotMob | LaLiga2 match results by jornada | Weekly |
| `rz_raw.fotmob_player_match_stats` | FotMob | Per-player stats per match (rating, goals, assists, passes, tackles, duels, xA) | Weekly |
| `rz_raw.fotmob_shots` | FotMob | Shot-level data with xG coordinates | Weekly |
| `rz_raw.fotmob_team_match_stats` | FotMob | Team totals per match (possession, shots, passes, duels, xG) | Weekly |

Tables are **append-only, partitioned by match date, clustered by jornada** — past seasons stay queryable alongside the current one.

Current coverage: **LaLiga2 (Segunda División) 2024-25 and 2025-26**. 1RFEF coverage is a gap — FotMob provides only match results for that tier (no player stats); alternative source pending.

---

## Pipeline

```
Cloud Scheduler (Tuesdays)
  ├── 06:00 CET → Cloud Run: rz-scraper-transfermarkt → rz_raw.transfermarkt_squad
  └── 06:30 CET → Cloud Run: rz-scraper-fotmob       → rz_raw.fotmob_*
```

- **Historical backfill**: run once per season — `INCREMENTAL=false`, optionally set `SCRAPE_START/END`
- **Weekly incremental**: `INCREMENTAL=true` in scheduler — scrapes last 8 days only

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
