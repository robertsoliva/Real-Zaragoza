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

Current coverage: **LaLiga2 2024-25 and 2025-26 + 1RFEF 2024-25 and 2025-26**.

---

## Pipeline

```
Cloud Scheduler (Tuesdays)
  ├── 06:00 CET → Cloud Run: rz-scraper-transfermarkt → rz_raw.transfermarkt_squad
  └── local cron → scraper_sofascore.py (INCREMENTAL=true) → rz_raw.sofascore_*
```

- **Historical backfill**: run once per season locally — `INCREMENTAL=false`, set `TOURNAMENT_ID` + `SEASON_ID`
- **Weekly incremental**: `INCREMENTAL=true` — scrapes last 14 days only (SofaScore blocks GCP IPs; runs locally)

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
