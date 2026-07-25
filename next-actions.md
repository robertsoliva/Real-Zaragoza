# Next Actions

Forward-looking only — pending items by category. Completed items graduate to `wiki/log.md`; they don't live here.

---

## Active

- **SofaScore backfill (10 leagues)** — Eredivisie, Belgian Pro League, Liga Portugal, Bundesliga, 2. Bundesliga, Premier League, La Liga, Serie A, Ligue 1, + gap fills (J1, MLS, Serie B, Norwegian, Korean). 28 seasons in queue, 6 slots/day. Expected completion ~2026-07-30.
- **1RFEF 2026-27 season ID** — Zaragoza's actual playing season. Run `python seasons_lookup.py 17073` to find it; add to `sofascore_queue.txt` and `run_weekly_sofascore.sh` once available.

---

## Sporting analysis

- **LaLiga2 2025-26 squad benchmarks** — produce team style profiles for all LaLiga2 2025-26 sides (`gold.fct_team_season_stats`). Useful for pre-season opponent analysis.
- **Match outcome model** — predict Zaragoza fixtures using historical form, opponent stats, home/away patterns. Feature set ready in `gold.fct_rz_matches` + `gold.fct_team_season_stats`. Approach TBD (logistic regression / xG-based).

---

## Data pipeline

- **1RFEF 2024-25 anomaly** — only ~100 matches loaded (expected ~380+). Re-queued at top of queue (PRIORITY 0) to re-scrape — will confirm if SofaScore exposes more rounds now or if it's a structural gap (playoff-only coverage for that season).
- **WC `league_name` fix** — rows from initial WC backfill have `league_name = "tournament_16"` not `"FIFA World Cup"`. Fix: add `CASE WHEN tournament_id = "16" THEN "FIFA World Cup" ELSE league_name END` in `bronze/matches.sql`. Until then filter by `tournament_id = "16"`.

---

## Infrastructure

- **Transfermarkt quarterly run (Oct 1 2026)** — `rz-tm-scraper` Cloud Run Job is blocked by Cloudflare from GCP. Must run locally: `python pipeline/cloud-run/scrapers/scraper_transfermarkt_leagues.py` (or `bash pipeline/run_transfermarkt_leagues.sh`). Cloud Scheduler `rz-tm-scraper-quarterly` will fire but do nothing useful from GCP. Until a curl_cffi/local-proxy workaround is found, treat as a manual quarterly task.
- **Capology enrichment in scouting** — enrich `agg_scouting_player_season` with wage data from `silver.capology_wages` (join on normalised name+club, same pattern as TM join).
- **Cloud Monitoring alerts** — alert on Cloud Run Job failure (`rz-dbt-refresh`, `rz-tm-scraper`, `rz-capology-scraper`) and optional BQ query cost threshold.

---

## Wiki

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
