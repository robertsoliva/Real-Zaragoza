# Next Actions

Forward-looking only — pending items by category. Completed items graduate to `wiki/log.md`; they don't live here.

---

## Active

- **SofaScore backfill** — Eredivisie, Belgian Pro League, Liga Portugal, Bundesliga, 2. Bundesliga, Premier League, La Liga, Serie A, Ligue 1 + gap fills (J1, MLS, Serie B, Norwegian, Korean). ~5–10 seasons remaining as of 2026-07-26. Expected completion ~2026-07-30.
- **1RFEF 2026-27** — season_id=97382 confirmed, queued at PRIORITY 6. Add to `run_weekly_sofascore.sh` when the season kicks off (Aug 2026).

---

## Sporting analysis

- **Player profile clustering — extend coverage to SofaScore-only players** — `gold.agg_player_profiles` (built 2026-07-29) only covers the ~7k player-seasons with a real TM granular position match. Players with just a broad SofaScore D/M/F/G code aren't scored — there's no safe way to pick a single position group for them (a broad "M" could be DM, CM, or CAM, each scored on different features). Needs a real design decision (e.g. a secondary lightweight classifier D/M/F → 7-group, or just accept the coverage gap) before extending.
- **Player profile clustering — retrain cadence** — deliberately NOT part of the daily `rz-dbt-refresh` run (`agg_player_profiles` is tagged `player_clustering` and excluded via `--exclude tag:player_clustering` in the Cloud Run job's dbt command, so it's static between manual retrains, not recomputed daily for no reason). Retrain manually every 6-12 months, or opportunistically after a TM quarterly scrape:
  1. `python3 pipeline/cloud-run/player-clustering/impute_player_features.py` (rebuilds `ml.player_profile_features` from current data)
  2. `python3 pipeline/cloud-run/player-clustering/train_cluster_models.py` (retrains the 7 k-means models)
  3. `gcloud run jobs execute rz-dbt-refresh --region=europe-west1 --args="--select,tag:player_clustering" --wait` (rebuilds just `gold.agg_player_profiles`, reusing the deployed image's ENTRYPOINT/CMD split — no new infra needed)
- **Player profile clustering — wire into scouting/website** — join `gold.agg_player_profiles` to `gold.agg_scouting_player_season` (on sofascore_id + team_name + tournament_id + season_id) so archetype labels show up in scouting reports and the website scouting page.
- **LaLiga2 2025-26 squad benchmarks** — produce team style profiles for all LaLiga2 2025-26 sides (`gold.fct_team_season_stats`). Useful for pre-season opponent analysis.
- **Match outcome model** — predict Zaragoza fixtures using historical form, opponent stats, home/away patterns. Feature set ready in `gold.fct_rz_matches` + `gold.fct_team_season_stats`. Approach TBD (logistic regression / xG-based).

---

## Infrastructure

- **Transfermarkt quarterly run (Oct 1 2026)** — must run locally (GCP datacenter IPs blocked by Cloudflare). Run: `python pipeline/cloud-run/scrapers/scraper_transfermarkt_leagues.py`. Cloud Scheduler `rz-tm-scraper-quarterly` fires but does nothing useful from GCP.
- **Fix TM scraper column offset bug (Oct 1 2026)** — some TM competition pages have 9 `td.zentriert` cells per player row instead of 8, shifting all columns after nationality by +1. Affects contract_expiry, foot, signed_from (NULL for LaLiga2, Serie B, 2.Bundesliga, Ligue 2, etc.). Height fix was applied in silver_tm_players.sql. The scraper needs column detection by type (regex/header-based) rather than fixed `stats[n::8]` offsets. Fix before the Oct quarterly run.
- **Wage multiplier calibration** — multipliers in `predict_wages.py` are based on 2025 published averages. Re-check after each TM quarterly run once more per-league salary data becomes available.

---

## Wiki

- **Player pages** — one atomic page per first-team player; replace `squad.md` prose roster with a structured table + per-player pages. After TM data stabilises (next quarterly scrape: Oct 1 2026).
- **Sweep open items** — `current-situation.md` (Fernando López succession, institutional president), `squad.md` (2026-27 captaincy, at-risk players, Ander Herrera latest), `academy.md` (Francho/Azón renewals).
- **Season-by-season results** — generate from `gold.fct_rz_matches` once 2025-26 data is loaded; link from `history.md`.

---

## Website

Local demo in `website/`. Launch with `bash website/start.sh` (requires `ANTHROPIC_API_KEY`).

- **Squad cards** — update with 2026-27 confirmed signings (Hansson, Espiau, Herrera, González). `silver.rz_squad` will be populated after Oct 1 TM quarterly run.
- **Match results page** — from `gold.fct_rz_matches`.
- **Player detail pages** — per-player stat breakdown from `gold.fct_player_season_stats`.
- **League comparison views** — Zaragoza vs. LaLiga2 averages from `gold.agg_league_player_benchmarks`.
- **Deploy publicly** — once at least one full 2025-26 season is in BQ and the squad page is current.
