# Next Actions

Forward-looking only — pending items by category. Completed items graduate to `wiki/log.md`; they don't live here.

---

## Active

- **SofaScore backfill (4 leagues)** — Eredivisie (37), Belgian Pro League (38), Liga Portugal (238), 2. Bundesliga (35) added 2026-07-22. Loading via launchd cadence (4 slots/day). Expected completion ~2026-07-26.
- **1RFEF 2026-27 season ID** — Zaragoza's actual playing season. Run `python seasons_lookup.py 17073` to find it; add to `sofascore_queue.txt` and `run_weekly_sofascore.sh` once available.

---

## Sporting analysis

- **Scouting reports on 4 new signings** — Emil Hansson (LW), Edu Espiau (CF), Ander Herrera (MF/DM), Diego González (CB). All 2026-27 confirmed. Data exists for Hansson/Espiau/Herrera in SofaScore pipeline leagues. Use data-scout agent.
- **LaLiga2 2025-26 squad benchmarks** — now that backfills are largely complete, produce team style profiles for all LaLiga2 2025-26 sides (from `gold.fct_team_season_stats`). Useful for pre-season opponent analysis.
- **Match outcome model** — predict Zaragoza fixtures using historical form, opponent stats, home/away patterns. Feature set ready in `gold.fct_rz_matches` + `gold.fct_team_season_stats`. Approach TBD (logistic regression / xG-based).
- **Scouting backlog** — old reports (Bjørkan, Seol, Radunović, Sjøvold, Hansson, Espiau, Herrera, González, Akman, Suzuki) used the old 5-dimension system. Redo when next batch requested.

---

## Data pipeline

- **Capology first run** — scraper and Cloud Run Job (`rz-capology-scraper`) are deployed but `raw.capology_wages` is empty. Run once manually to seed it: `gcloud run jobs execute rz-capology-scraper --region europe-west1`. Covers top 5 EU leagues only (not LaLiga2/Serie B etc.) — useful for profiling targets from big leagues.
- **Weekly SofaScore automation** — update `run_weekly_sofascore.sh` to include all 20 active leagues once the backfill queue is cleared (~end of July 2026). Currently covers only LaLiga2 + 1RFEF.
- **1RFEF 2024-25 anomaly** — only ~100 matches loaded (expected ~380+). Likely SofaScore exposes only playoff rounds for this season via the rounds API. Investigate before deciding whether to re-backfill.
- **WC `league_name` fix** — rows from the initial WC backfill (before 2026-07-05) have `league_name = "tournament_16"` not `"FIFA World Cup"`. Fix: add `CASE WHEN tournament_id = "16" THEN "FIFA World Cup" ELSE league_name END` in `bronze/matches.sql`. Until then, filter WC data by `tournament_id = "16"`.

---

## Infrastructure

- **Cloud Monitoring alerts** — alert on Cloud Run Job failure (`rz-refresh-layers`, `rz-tm-scraper`, `rz-capology-scraper`) and optional BQ query cost threshold. Low priority until operationally critical.

---

## Wiki

- **`architecture.md`** — rewrite to reflect current dataset names, 20-league scope, Cloud Run Jobs, and medallion architecture. The existing page still references `rz_raw`, `WC_26`, and old infra.
- **Player pages** — one atomic page per first-team player; replace `squad.md` prose roster with a structured table + per-player pages. After TM data stabilises (next quarterly scrape: Oct 1 2026).
- **Sweep open items** — `current-situation.md` (Fernando López succession, institutional president), `squad.md` (2026-27 captaincy, at-risk players, Ander Herrera latest), `academy.md` (Francho/Azón renewals).
- **Season-by-season results** — generate from `gold.fct_rz_matches` once 2025-26 data is loaded; link from `history.md`.

---

## Website

Local demo in `website/`. Launch with `bash website/start.sh` (requires `ANTHROPIC_API_KEY`).

- **Squad cards** — update with 2026-27 confirmed signings (Hansson, Espiau, Herrera, González).
- **Match results page** — from `gold.fct_rz_matches`.
- **Player detail pages** — per-player stat breakdown from `gold.fct_player_season_stats`.
- **League comparison views** — Zaragoza vs. LaLiga2 averages from `gold.agg_league_player_benchmarks`.
- **Deploy publicly** — once at least one full 2025-26 season is in BQ and the squad page is current.
