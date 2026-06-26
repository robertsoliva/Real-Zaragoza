# Next Actions

Running backlog of ideas/future work for this repo. Not a wiki page — this tracks what to *build*, the wiki tracks what we *know*. Move items to "Done" with a date when finished instead of deleting, so we keep a record of when things shipped.

## Data pipeline

- [x] **Scraper — Transfermarkt.** `pipeline/cloud-run/scraper_transfermarkt.py` — verein/142, `/plus/1`, 32 players, full schema confirmed — 2026-06-26
- [ ] **Scraper — SofaScore.** Pull recent matches, team stats, and player stats via SofaScore's unofficial internal API. Target tables: `rz_raw.sofascore_matches`, `rz_raw.sofascore_match_stats`, `rz_raw.sofascore_player_stats`.
- [ ] **Cloud Run container.** Dockerfile + deploy `rz-scraper` to Cloud Run (Transfermarkt + SofaScore in one image); publishes to `rz-data-ingested`.
- [ ] **Cloud Function — BQ loader.** `rz-bq-loader`: Pub/Sub subscriber, validates schema, streams to `rz_raw`. Handle DLQ.
- [ ] **Cloud Scheduler job.** `rz-weekly-ingest` — Tuesday 06:00 CET trigger.
- [x] **`rz_processed` strategy decided.** Append-only raw + view deduplication on `(player_id, season_id)`. SQL in `wiki/data-pipeline.md` — 2026-06-26
- [x] **`rz_processed.squad_snapshots` view live in BQ** — 2026-06-26
- [ ] **`rz_processed.player_valuations` view.** Add after second weekly scrape so there's actual change data to query.
- [ ] **`rz_processed.season_results`.** Pending SofaScore scraper.
- [ ] **Monitoring.** Cloud Monitoring alerts on Pub/Sub backlog + Cloud Function error rate; set up when Cloud Function is deployed.

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
- [x] GCP project setup: APIs enabled, service account `rz-pipeline` created with minimum IAM roles, budget alert at €10/month — 2026-06-26
- [x] BQ datasets `rz_raw` and `rz_processed` created (europe-west1); `transfermarkt_squad` table live, 32 rows loaded — 2026-06-26
- [ ] Containerize scraper (Dockerfile) and deploy to Cloud Run as a job.
- [ ] Deploy Cloud Function with Pub/Sub trigger.
