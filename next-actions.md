# Next Actions

Running backlog for this repo. Not a wiki — tracks what to *build*. Move items to "Done" with a date instead of deleting.

---

## Data pipeline

### Done
- [x] **Transfermarkt scraper** — `scraper_transfermarkt.py`, verein/142 `/plus/1`, 32 players, full BQ schema — 2026-06-26
- [x] **FotMob scraper** — `scraper_fotmob.py`, LaLiga2 via date-iteration, per-player stats + shot maps — 2026-06-26
- [x] **Cloud Run + Scheduler — Transfermarkt** — `rz-scraper-transfermarkt`, `rz-weekly-ingest` Tuesdays 06:00 CET — 2026-06-26
- [x] **Cloud Run + Scheduler — FotMob** — `rz-scraper-fotmob`, `rz-weekly-fotmob` Tuesdays 06:30 CET — 2026-06-26
- [x] **BQ tables** — `rz_raw`: `transfermarkt_squad` (ingested_date partition), `fotmob_matches` + `fotmob_player_match_stats` + `fotmob_shots` (match_date partition, match_round cluster) — 2026-06-26
- [x] **LaLiga2 2024-25 backfill** — executed 2026-06-26 (execution `rz-scraper-fotmob-s6ds6`) — 2026-06-26
- [x] **`rz_processed` strategy** — append-only raw + view dedup on `(player_id, season_id)` — 2026-06-26
- [x] **Incremental mode** — `INCREMENTAL=true` env var → last 8 days; weekly scheduler uses this — 2026-06-26

### Pending
- [ ] **Verify 2024-25 backfill** — query `rz_raw.fotmob_matches`: expect ~462 rows; `fotmob_player_match_stats`: ~13k rows
- [ ] **LaLiga2 2025-26 backfill** — Zaragoza's season just finished. Run with `SCRAPE_START=2025-07-01 SCRAPE_END=2026-06-26` then revert to `INCREMENTAL=true`
- [ ] **1RFEF player stats** — FotMob only has `lower` coverage (no player stats). Zaragoza play in 1RFEF from 2026-27. Priority: (1) test SofaScore from Cloud Run IPs — home IP was blocked but Cloud Run IPs differ; (2) FBRef scraper (free, has 1RFEF); (3) API-Football (paid)
- [ ] **Dedup view** — `rz_processed.match_dedup`: incremental runs overlap → same match_id may appear twice. View on `(match_id)` keeping latest `ingested_at`
- [ ] **`rz_processed.season_results`** — W/D/L, goal diff, cumulative points from `fotmob_matches` once data confirmed
- [ ] **`rz_processed.player_valuations`** — time series of market value from `transfermarkt_squad`; add after second weekly scrape
- [ ] **Cloud Function** — `rz-bq-loader` Pub/Sub subscriber; deferred until fan-out is needed

---

## Analysis & predictions

- [ ] **LaLiga2 2024-25 stats analysis** — form, xG trends, head-to-head, defensive and attacking profiles for all 22 teams; depends on BQ backfill
- [ ] **Player comparison tool** — compare Zaragoza squad against league averages and specific targets; depends on `fotmob_player_match_stats`
- [ ] **Match outcome model** — predict Zaragoza fixtures; feature set from FotMob + Transfermarkt; approach TBD

---

## Wiki content

### Done
- [x] Club pages: `history.md`, `current-situation.md`, `finances.md`, `squad.md`, `identity-fan-culture.md`, `records.md`, `academy.md` — 2026-06-24
- [x] `wiki/index.md`, `wiki/architecture.md` (canonical technical reference) — 2026-06-26

### Pending
- [ ] **Season-by-season results table** — generate from FotMob data once loaded; link from `history.md`
- [ ] **Player pages** — one atomic page per first-team player; replace `squad.md` prose roster with structured table; after Transfermarkt data stable
- [ ] **Sweep open items** — `current-situation.md` (Fernando López succession), `squad.md` (2026-27 captaincy, at-risk players), `academy.md` (Ander Herrera return, Francho/Azón renewals)

---

## Infrastructure

### Done
- [x] GCP project `real-zaragoza-500608` — APIs enabled, service account `rz-pipeline`, budget alert €10/month — 2026-06-26
- [x] BQ datasets `rz_raw` + `rz_processed` (europe-west1) — 2026-06-26
- [x] Artifact Registry `rz-images`, Cloud Build pipeline — 2026-06-26

### Pending
- [ ] **Cloud Monitoring alerts** — Pub/Sub backlog + Cloud Run failure rate; add when Cloud Function is deployed
