# Next Actions

Forward-looking only — pending items by category. Completed items graduate to `wiki/log.md`; they don't live here.

---

## Active

- **SofaScore backfill (4 new leagues)** — Eredivisie (37), Belgian Pro League (38), Liga Portugal (238), 2. Bundesliga (35) added 2026-07-22. Loading via launchd cadence. Expected completion ~2026-07-26.
- **Transfermarkt multi-league initial scrape** — running now (PID 87614, started 2026-07-24). All 19 active leagues; data lands in `rz_raw.transfermarkt_players` → `rz_gold.gold_tm_players`.

---

## Data pipeline

- **1RFEF 2026-27** — season ID not yet on SofaScore (~July 2026). When available: add to queue and weekly script.
- **1RFEF 2024-25 anomaly** — only 100 matches loaded (expected ~380+). Likely SofaScore exposes only playoff rounds for this season via the rounds API. Investigate before deciding whether to re-backfill.
- **WC league_name fix** — rows from the initial WC backfill (before 2026-07-05) have `league_name = "tournament_16"` not `"FIFA World Cup"`. Fix: normalise in `bronze_matches` with a CASE on `tournament_id`. Until then, always filter WC data by `tournament_id = "16"`.
- **`rz_gold.season_results`** — W/D/L, GD, cumulative points per team per season. Starting point: `rz_gold.gold_zaragoza_matches` + `rz_silver.silver_team_stats` for all teams. Add SQL to `pipeline/sql/gold/`.
- **`rz_silver.player_valuations`** — time series of market value per player per season, joinable with gold_player_season. Source: `rz_bronze.bronze_tm_players` (all leagues) and `rz_bronze.bronze_squad` (Zaragoza). Add SQL to `pipeline/sql/silver/`.
- **Move TM scrapers to Cloud Run** — `scraper_transfermarkt.py` (Zaragoza-only, weekly) and `scraper_transfermarkt_leagues.py` (all leagues, weekly) are candidates for Cloud Run Jobs + Cloud Scheduler triggers. TM doesn't block GCP IPs. Would remove the only remaining local scraper dependency.
- **Weekly SofaScore automation** — update `run_weekly_sofascore.sh` to include all 20 active leagues once backfills are fully done.

---

## Infrastructure

- **Cloud Monitoring alerts** — set up alerts on Cloud Run job failure (rz-refresh-layers) and optional BQ query cost threshold. Low priority until pipeline is fully GCP-hosted.
- **Cloud Function `rz-bq-loader`** — Pub/Sub subscriber for fan-out; deferred until SofaScore scraper can move off local machine or a second data source requires it.

---

## Analysis & predictions

- **Standardised agent report structures** — data-scout and match-analyst use ad-hoc column groupings; define enforced output templates that map to the [Attacking/Passing/Defending/Physical] schema labels.
- **LaLiga2 2025-26 benchmarks** — form, head-to-head, defensive and attacking profiles for all 22 teams; now possible with backfill complete.
- **Player comparison tool** — compare Zaragoza squad against league averages and specific targets; depends on `sofascore_player_match_stats`.
- **Match outcome model** — predict Zaragoza fixtures; feature set from SofaScore + Transfermarkt; approach TBD.
- **Scouting: redo old reports on new 6-dimension system** — Bjørkan, Seol, Radunović, Sjøvold, Hansson, Espiau, Herrera, González, Akman, Suzuki all use the old 5-dimension system without Player Quality/Level. Update when next report batch is requested.

---

## Wiki

- **Season-by-season results table** — generate from SofaScore data once loaded; link from `history.md`.
- **Player pages** — one atomic page per first-team player; replace `squad.md` prose roster with a structured table; after Transfermarkt data is stable.
- **Sweep open items** — `current-situation.md` (Fernando López succession, institutional president), `squad.md` (2026-27 captaincy, at-risk players, Ander Herrera), `academy.md` (Francho/Azón renewals).

---

## Website

Local demo in `website/`. Launch with `bash website/start.sh` (requires `ANTHROPIC_API_KEY`).

- **Squad page** — update Transfermarkt cards with 2026-27 signings once multi-league TM scrape stabilises.
- **Match results page** — from `gold_zaragoza_matches`.
- **Player detail pages** — per-player stat breakdown.
- **League comparison views** — Zaragoza vs. LaLiga2 averages.
- **Deploy publicly** — once backfills are stable and at least one full 2025-26 season is in BQ.
