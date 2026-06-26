# Next Actions

Running backlog of ideas/future work for this repo. Not a wiki page — this tracks what to *build*, the wiki tracks what we *know*. Move items to "Done" with a date when finished instead of deleting, so we keep a record of when things shipped.

## Data pipeline

- [x] **Scraper — Transfermarkt.** `pipeline/cloud-run/scraper_transfermarkt.py` — verein/142, `/plus/1`, 32 players, full schema confirmed — 2026-06-26
- [x] **Scraper — FotMob.** `pipeline/cloud-run/scraper_fotmob.py` — LaLiga2 2024-25 full season; date-iteration strategy; per-match player stats (rating, minutes, goals, assists, passes, touches, defense, duels); shot maps on xG-coverage matches. Smoke-tested locally (11 matches, 345 player rows) — 2026-06-26
- [x] **Cloud Run + Scheduler — Transfermarkt.** `rz-scraper-transfermarkt` job deployed; `rz-weekly-ingest` scheduler firing Tuesdays 06:00 CET. Scraper → BQ, no manual steps — 2026-06-26
- [x] **FotMob Cloud Run deployment.** `rz-scraper-fotmob` job live (europe-west1); `rz-weekly-fotmob` scheduler Tuesdays 06:30 CET; 2024-25 historical backfill launched 2026-06-26 — 2026-06-26
- [x] **FotMob incremental mode.** `INCREMENTAL=true` env var: scrapes last 8 days. Cloud Run job updated; weekly scheduler will use this mode — 2026-06-26
- [ ] **FotMob BQ row count check.** After backfill completes, query `rz_raw.fotmob_matches` and `rz_raw.fotmob_player_match_stats` to confirm ~462 matches and ~13k player rows ingested.
- [ ] **Cloud Function — BQ loader (Pub/Sub).** Add when fan-out is needed (Slack alerts, wiki auto-update). Not needed yet.
- [x] **`rz_processed` strategy decided.** Append-only raw + view deduplication on `(player_id, season_id)`. SQL in `wiki/data-pipeline.md` — 2026-06-26
- [x] **`rz_processed.squad_snapshots` view live in BQ** — 2026-06-26
- [ ] **`rz_processed.player_valuations` view.** Add after second weekly scrape so there's actual change data to query.
- [ ] **`rz_processed.season_results`.** Pending SofaScore scraper.
- [ ] **Monitoring.** Cloud Monitoring alerts on Pub/Sub backlog + Cloud Function error rate; set up when Cloud Function is deployed.

## Analysis & predictions

- [ ] Stats analysis on players and matches once FotMob historical backfill lands: form, head-to-head, performance trends, player comparisons across the 22 LaLiga2 teams.
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
- [x] Containerize Transfermarkt scraper and deploy to Cloud Run (`rz-scraper-transfermarkt`, image in `rz-images` Artifact Registry repo) — 2026-06-26
- [x] Containerize FotMob scraper (`Dockerfile.fotmob`) and deploy to Cloud Run as `rz-scraper-fotmob` — 2026-06-26
- [ ] Deploy Cloud Function with Pub/Sub trigger (deferred — add when fan-out is needed).
