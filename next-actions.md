# Next Actions

Running backlog for this repo. Not a wiki — tracks what to *build*. Move items to "Done" with a date instead of deleting.

---

## Data pipeline

### Done
- [x] **Transfermarkt scraper** — `scraper_transfermarkt.py`, verein/142 `/plus/1`, 32 players, full BQ schema — 2026-06-26
- [x] **Cloud Run + Scheduler — Transfermarkt** — `rz-scraper-transfermarkt`, `rz-weekly-ingest` Tuesdays 06:00 CET — 2026-06-26
- [x] **`rz_processed` strategy** — append-only raw + view dedup on `(player_id, season_id)` — 2026-06-26
- [x] **SofaScore scraper** — `scraper_sofascore.py`; `curl_cffi` Chrome TLS impersonation; round-based iteration; player stats, team stats, shot maps; incremental mode (last 14 days); verified working locally — 2026-06-28
- [x] **SofaScore BQ schemas** — `sofascore_matches`, `sofascore_player_match_stats`, `sofascore_shots`, `sofascore_team_match_stats` — 2026-06-28
- [x] **SofaScore IDs discovered** — LaLiga2=54 (SID 62048/77558), 1RFEF=17073 (SID 64430/77727), Real Zaragoza=2815 — 2026-06-28

### Pending
- [x] **LaLiga2 backfills** — 2024-25 (484 matches, 21,293 player rows) and 2025-26 (484 matches, 21,574 player rows) loaded successfully 2026-07-01 with updated schema (league_name, tournament_id, category labels)
- [x] **1RFEF 2024-25 partial** — 100 matches loaded; anomaly: expected ~380+ matches. Likely SofaScore exposes only playoff rounds for this season via the rounds API. Needs investigation.
- [ ] **League retry** — 9 seasons (1RFEF 2025-26, Serie B × 2, Ligue 2 × 2, Romanian SuperLiga × 2, J1 × 2) failed 2026-07-01 due to 24-hour IP ban. `backfill_retry.sh` ready (15-min inter-league pauses). Launch when IP clears (~13:30 2026-07-02).
- [ ] **WC_26 setup** — BQ dataset + 4 tables created 2026-07-01. Find WC 2026 tournament/season IDs via `python3 seasons_lookup.py 17`, patch `run_daily_wc26.sh`, run historical backfill from 2026-06-11, register `com.realzaragoza.wc26-daily.plist` for daily 09:00 scrape.
- [ ] **Verify backfills landed** — after league retry completes, query `rz_raw.sofascore_matches` grouped by `(tournament_id, season_id)` to confirm row counts
- [ ] **Weekly automation** — `rz-weekly-sofascore` Cloud Run scheduler is paused. Need to set up local cron (launchd on Mac) or non-GCP host for ongoing 1RFEF data. See architecture.md.
- [ ] **1RFEF 2026-27** — season ID not yet on SofaScore (~July 2026). When available: run local backfill with `TOURNAMENT_ID=17073 SEASON_ID=<new_sid>`, then set up weekly local run.
- [ ] **Dedup view** — `rz_processed.match_dedup` on `(match_id)` keeping latest `ingested_at`
- [ ] **`rz_processed.season_results`** — W/D/L, goal diff, cumulative points from `sofascore_matches` once data confirmed
- [ ] **`rz_processed.player_valuations`** — time series of market value from `transfermarkt_squad`; add after second weekly scrape
- [ ] **Cloud Function** — `rz-bq-loader` Pub/Sub subscriber; deferred until fan-out is needed

---

## Analysis & predictions

- [ ] **Standardised agent report structures** — data-scout and match-analyst currently use ad-hoc column groupings; define enforced output templates that map directly to the [Attacking/Passing/Defending/Physical] schema labels so reports self-update as new stats are added
- [ ] **LaLiga2 2024-25 stats analysis** — form, head-to-head, defensive and attacking profiles for all 22 teams; depends on BQ backfill
- [ ] **Player comparison tool** — compare Zaragoza squad against league averages and specific targets; depends on `sofascore_player_match_stats`
- [ ] **Match outcome model** — predict Zaragoza fixtures; feature set from SofaScore + Transfermarkt; approach TBD

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
