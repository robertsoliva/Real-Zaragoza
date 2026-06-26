# Next Actions

Running backlog of ideas/future work for this repo. Not a wiki page — this tracks what to *build*, the wiki tracks what we *know*. Move items to "Done" with a date when finished instead of deleting, so we keep a record of when things shipped.

## Data pipeline

- [ ] **Scraper — Transfermarkt.** Implement Cloud Run container that scrapes squad, market values, and contract data. Strategy TBD: HTML scraping or `transfermarkt-scraper` library. Target table: `rz_raw.transfermarkt_squad`.
- [ ] **Scraper — SofaScore.** Implement Cloud Run container that pulls recent matches, team stats, and player stats via SofaScore's unofficial internal API. Target tables: `rz_raw.sofascore_matches`, `rz_raw.sofascore_match_stats`, `rz_raw.sofascore_player_stats`.
- [ ] **Cloud Function — BQ loader.** Pub/Sub subscriber that validates schema and streams rows into `rz_raw`. Handle dead-letter queue for failed messages.
- [ ] **Cloud Scheduler job.** Wire up the Tuesday 06:00 CET trigger for the Cloud Run scraper job.
- [ ] **`rz_processed` views/tables.** Define `squad_current`, `player_valuations`, `season_results` — decide materialized vs. views.
- [ ] **Monitoring.** Cloud Monitoring alerts on Pub/Sub backlog + Cloud Function error rate.

## Analysis & predictions

- [ ] Stats analysis on players and matches once the SofaScore/Transfermarkt pull lands: form, head-to-head, performance trends.
- [ ] Match outcome prediction model for upcoming Real Zaragoza fixtures — approach/tooling TBD, depends on the data pull above.

## Wiki content

- [x] Reconcile `history.md` + `current-situation.md` against realzaragoza.com and Wikipedia — 2026-06-24
- [x] Institution/football deep-dive pages: `finances.md`, `squad.md`, `identity-fan-culture.md`, `records.md`, `academy.md` — 2026-06-24
- [x] `wiki/index.md` navigation and status index (consolidated from `wiki/README.md`) — 2026-06-26
- [x] Contribute-text skill, log-entry and wiki-page templates — 2026-06-26
- [x] Data pipeline architecture documented in `wiki/data-pipeline.md` — 2026-06-26
- [ ] Season-by-season results table (full history) — generate from SofaScore pull once live; link from `wiki/history.md`.
- [ ] Player pages — one atomic page per current first-team player once Transfermarkt data lands; also replace `wiki/squad.md` prose roster with a structured table and give `wiki/academy.md` a current graduate list.
- [ ] Standing task: sweep every wiki page's "Open items" section periodically for things now resolvable — several are time-sensitive right now (institutional president / Fernando López succession in `current-situation.md`; 2026–27 captaincy and "at risk" players in `squad.md`; Ander Herrera return and Francho/Azón renewals in `academy.md`).

## Infrastructure

- [x] Clone repo locally, scaffold `wiki/` + `next-actions.md` + `.claude/` — 2026-06-24
- [x] Storage layer decided: Google BigQuery (`rz_raw` + `rz_processed` datasets) — 2026-06-26
- [x] Refresh cadence decided: weekly, every Tuesday, via Cloud Scheduler — 2026-06-26
- [x] Pipeline architecture decided: Cloud Scheduler → Cloud Run → Pub/Sub → Cloud Function → BQ — 2026-06-26
- [x] Repo layout decided: `data/` for local snapshots (gitignored contents), `pipeline/` for container/function code — 2026-06-26
- [ ] GCP project setup: create project, enable APIs (Cloud Run, Cloud Functions, Pub/Sub, BigQuery, Cloud Scheduler, Secret Manager), create service account with minimum required roles.
- [ ] Create BQ datasets `rz_raw` and `rz_processed` with correct region and partition settings.
- [ ] Containerize scraper (Dockerfile) and deploy to Cloud Run as a job.
- [ ] Deploy Cloud Function with Pub/Sub trigger.
