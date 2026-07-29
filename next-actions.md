# Next Actions

Forward-looking only — pending items by category. Completed items graduate to `wiki/log.md`; they don't live here.

---

## Active

- **SofaScore backfill** — Eredivisie, Belgian Pro League, Liga Portugal, Bundesliga, 2. Bundesliga, Premier League, La Liga, Serie A, Ligue 1 + gap fills (J1, MLS, Serie B, Norwegian, Korean). ~5–10 seasons remaining as of 2026-07-26. Expected completion ~2026-07-30.
- **1RFEF 2026-27** — season_id=97382 confirmed, queued at PRIORITY 6. Add to `run_weekly_sofascore.sh` when the season kicks off (Aug 2026).

---

## Sporting analysis

- **Player profile clustering** — K-means clustering to define player archetypes within each position. Agreed design:
  - **Segmentation:** TM position (granular: CB, FB, DM, CM, CAM, Winger, CF) — not SofaScore's broad F/M/D codes. Train only on players with TM position + ≥450 min; apply to SofaScore-only players using SofaScore position as fallback.
  - **Models:** One BQML k-means per position group (7 models). Train in BQ so labels can be applied via SQL.
  - **k:** Do NOT pre-define. For each position, run k=2 through k=8 and use elbow + silhouette score to find the optimal k empirically. Name clusters after inspecting centroids (`ML.CENTROIDS()`).
  - **Features:** Position-specific (e.g. Winger: shots_p90, key_passes_p90, cross_acc_pct, tackles_p90, touches_p90; CF: goals_p90, shots_p90, aerial_win_pct, key_passes_p90, touches_p90, tackles_p90; CB: aerial_win_pct, duel_win_pct, tackles_p90, interceptions_p90, pass_acc_pct, long_ball_acc_pct).
  - **NULL handling:** MICE imputation (sklearn `IterativeImputer`) — predicts missing stats from correlated features within the same position group. Run in Python, write imputed dataset back to BQ, then train BQML on the clean table.
  - **Output:** `gold.agg_player_profiles` (player_name, team_name, season_id, position_group, cluster_id, profile_label). Join to `gold.agg_scouting_player_season` for use in scouting reports and website.
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
