# Next Actions

Forward-looking only — pending items by category. Completed items graduate to `wiki/log.md`; they don't live here.

---

## Active

- **SofaScore backfill (10 leagues)** — Eredivisie, Belgian Pro League, Liga Portugal, Bundesliga, 2. Bundesliga, Premier League, La Liga, Serie A, Ligue 1, + gap fills (J1, MLS, Serie B, Norwegian, Korean). ~21 seasons remaining, 6 slots/day. Expected completion ~2026-07-29.
- **1RFEF 2026-27 season ID** — season_id=97382 confirmed. Queued at PRIORITY 6 in `sofascore_queue.txt`. Add to `run_weekly_sofascore.sh` once the season starts (Aug 2026).

---

## Sporting analysis

- **LaLiga2 2025-26 squad benchmarks** — produce team style profiles for all LaLiga2 2025-26 sides (`gold.fct_team_season_stats`). Useful for pre-season opponent analysis.
- **Match outcome model** — predict Zaragoza fixtures using historical form, opponent stats, home/away patterns. Feature set ready in `gold.fct_rz_matches` + `gold.fct_team_season_stats`. Approach TBD (logistic regression / xG-based).

---

## Infrastructure

- **Transfermarkt quarterly run (Oct 1 2026)** — `rz-tm-scraper` Cloud Run Job is blocked by Cloudflare from GCP. Must run locally: `python pipeline/cloud-run/scrapers/scraper_transfermarkt_leagues.py` (or `bash pipeline/run_transfermarkt_leagues.sh`). Cloud Scheduler `rz-tm-scraper-quarterly` will fire but do nothing useful from GCP. Until a curl_cffi/local-proxy workaround is found, treat as a manual quarterly task.
- **Wage model lower-league discount** — `ml.wage_regression` is trained on top-5 EU leagues only; predictions for LaLiga2/Serie B etc. are biased upward. Apply a post-prediction league-tier multiplier (e.g. LaLiga2 ≈ 35% of La Liga) once aggregate salary data per division is sourced. See `wiki/wage-model.md` open items.

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
