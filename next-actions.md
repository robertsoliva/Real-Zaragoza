# Next Actions

Forward-looking only — pending items by category. Completed items graduate to `wiki/log.md`; they don't live here.

---

## Active

- **Backfill cadence** — 1 season/slot × 2/day via `run_next_from_queue.sh` (launchd 09:00 + 18:00). Remaining queue: Ligue 2 × 2, Romanian SuperLiga × 2, J1 × 2, 1RFEF 2025-26, Turkish × 2, Norwegian × 2, Austrian × 2, Korean × 2 (15 seasons).
- **WC 2026 daily incremental** — `com.realzaragoza.wc26-daily.plist` registered 2026-07-05. Fires daily at 09:00 through July 19 (WC final).

---

## Data pipeline

- **Verify backfills landed** — after each league completes, run `SELECT tournament_id, season_id, COUNT(*) FROM rz_raw.sofascore_matches GROUP BY 1,2` to confirm row counts.
- **Weekly automation** — once backfills are done, update `run_weekly_sofascore.sh` to include all active leagues and ensure launchd Tuesday job is registered.
- **1RFEF 2026-27** — season ID not yet on SofaScore (~July 2026). When available: add to queue and weekly script.
- **1RFEF 2024-25 anomaly** — only 100 matches loaded (expected ~380+). Likely SofaScore exposes only playoff rounds for this season via the rounds API. Investigate before deciding whether to re-backfill.
- **WC league_name fix** — rows from the initial WC backfill (before 2026-07-05) have `league_name = "tournament_16"` not `"FIFA World Cup"`. Fix: either re-backfill or normalise in `bronze_matches` with a CASE on `tournament_id`. Until then, always filter WC data by `tournament_id = "16"`.
- **`rz_gold.season_results`** — W/D/L, GD, cumulative points per team per season. Starting point: `rz_gold.gold_zaragoza_matches` + `rz_silver.silver_team_stats` for all teams. Add SQL to `pipeline/sql/gold/`.
- **`rz_silver.player_valuations`** — time series of market value from `rz_bronze.bronze_squad`; add after second weekly scrape. Add SQL to `pipeline/sql/silver/`.
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
