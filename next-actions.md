# Next Actions

Forward-looking only — pending items by category. Completed items graduate to `wiki/log.md`; they don't live here.

---

## Active

- **Backfill cadence** — 1 season/slot × 2/day via `run_next_from_queue.sh` (launchd 09:00 + 18:00). IP ban clears ~11:17 on 2026-07-04. Remaining queue: Ligue 2 × 2, Romanian SuperLiga × 2, J1 × 2, 1RFEF 2025-26 (7 seasons).
  - Register plists before Sunday: `launchctl load ~/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/schedules/com.realzaragoza.sofascore-9am.plist` (and 6pm variant)
- **WC 2026 (priority)** — tournament_id=17 confirmed; season_id still TODO. Run `python3 seasons_lookup.py 17` once IP clears, patch `run_daily_wc26.sh`, register `com.realzaragoza.wc26-daily.plist`, then run full backfill from 2026-06-11. WC final is July 19 — time-sensitive.

---

## Data pipeline

- **New leagues — ID lookup** — run `python3 seasons_lookup.py 52 57 45 55` once IP clears to confirm tournament IDs and season IDs for Turkish Süper Lig, Norwegian Eliteserien, Austrian Bundesliga, Korean K League 1. Fill in `sofascore_queue.txt` (currently TODO). Both 2024 and 2025/26 seasons each.
- **Verify backfills landed** — after each league completes, query `rz_raw.sofascore_matches GROUP BY tournament_id, season_id` to confirm row counts.
- **Weekly automation** — once backfill is done, update `run_weekly_sofascore.sh` to include all active leagues and ensure launchd Tuesday job is registered.
- **1RFEF 2026-27** — season ID not yet on SofaScore (~July 2026). When available: add to queue and weekly script.
- **1RFEF 2024-25 anomaly** — only 100 matches loaded (expected ~380+). Likely SofaScore exposes only playoff rounds for this season via the rounds API. Investigate before deciding whether to re-backfill.
- **Dedup view** — `rz_processed.match_dedup` on `(match_id)` keeping latest `ingested_at`.
- **`rz_processed.season_results`** — W/D/L, goal diff, cumulative points from `sofascore_matches` once backfills confirmed.
- **`rz_processed.player_valuations`** — time series of market value from `transfermarkt_squad`; add after second weekly scrape.
- **Cloud Function** — `rz-bq-loader` Pub/Sub subscriber; deferred until fan-out is needed.

---

## Analysis & predictions

- **Standardised agent report structures** — data-scout and match-analyst use ad-hoc column groupings; define enforced output templates that map to the [Attacking/Passing/Defending/Physical] schema labels.
- **LaLiga2 2024-25 stats analysis** — form, head-to-head, defensive and attacking profiles for all 22 teams; depends on BQ backfill.
- **Player comparison tool** — compare Zaragoza squad against league averages and specific targets; depends on `sofascore_player_match_stats`.
- **Match outcome model** — predict Zaragoza fixtures; feature set from SofaScore + Transfermarkt; approach TBD.

---

## Wiki

- **Season-by-season results table** — generate from SofaScore data once loaded; link from `history.md`.
- **Player pages** — one atomic page per first-team player; replace `squad.md` prose roster with a structured table; after Transfermarkt data is stable.
- **Sweep open items** — `current-situation.md` (Fernando López succession, institutional president), `squad.md` (2026-27 captaincy, at-risk players, Ander Herrera), `academy.md` (Francho/Azón renewals).

---

## Infrastructure

- **Cloud Monitoring alerts** — Pub/Sub backlog + Cloud Run failure rate; add when Cloud Function is deployed.

---

## Website (long-term)

**Prerequisite: data layer must be stable** — backfills complete, weekly automation running, at least one full season of player/team stats queryable.

- **Real Zaragoza stats website** — public-facing web app modelled on [atleticostats.com](https://atleticostats.com/home). Covers all club dimensions: match results and stats, player profiles and season stats, squad overview, scouting/comparison views, and institutional info from the wiki. Reads from BQ via a backend API layer. Scope and tech stack TBD once data is ready.
