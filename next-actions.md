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

## Infra + ETL improvements

Flagged 2026-07-29 from a full read-through of the pipeline (raw → bronze → silver → gold). Tackle one by one — not urgent individually, but several are silent-failure modes that could already be degrading data quality without anyone noticing.

**Data quality / process**

- **No identity crosswalk between sources — everything is name-string matching.** SofaScore player → TM player, SofaScore club → TM club, and TM → Capology are all joined on `LOWER(TRIM(name))`, with no `player_id` bridge table between SofaScore IDs and TM IDs. Two different players sharing a name (common for youth/South American players) will silently collide or silently produce NULLs, with no error surfaced anywhere.
- **`silver_tm_players` dedups player+club+season, but `silver_bqml_wages` dedups by player name only, ignoring club** (`pipeline/dbt/models/silver/silver_bqml_wages.sql` — the SQL comment admits this is a deliberate workaround for players who transferred between the TM scrape and the season being scored). Two same-named players anywhere across all 25 leagues will merge into one wage prediction. Conscious tradeoff at the time, but a real correctness gap.
- **`club_name_aliases.csv` (`pipeline/dbt/seeds/club_name_aliases.csv`) is a hand-maintained seed with no coverage check.** Every promotion/relegation or new club across the 25 pipeline leagues needs a manual alias row added, or `gold.agg_scouting_player_season` silently loses that club's market-value/wage join — no error, no test, just NULLs. Nothing in the pipeline reports "X% of players failed to match a TM club this run," so degradation is invisible until someone notices missing data by eye.
- **No visible dbt tests** (`unique`, `not_null`, `relationships`) — only descriptions exist in `schema.yml` per the stated convention. Given how much of gold depends on fuzzy name joins and hand-maintained mappings (club aliases, `dim_league` country lookup, cluster labels), this pipeline specifically needs uniqueness/referential tests on grain keys (e.g. `fct_player_season_stats` grain, `dim_player.player_id`). Confirm whether any exist today, then add tests where missing.
- **Cluster labels in `gold.agg_player_profiles` are hand-assigned and can silently desync from the model.** The model's own SQL comment warns that `CENTROID_ID` ordering can shift between retrains, but the `CASE CENTROID_ID WHEN 1 THEN 'Dominant Aerial CB' ...` label mapping isn't re-verified automatically. Retraining `ml.player_cluster_*` without also re-checking `ML.CENTROIDS` and updating labels produces confidently-wrong archetype names with no error. (Already noted as a re-verify step in the sporting-analysis retrain checklist above — this entry is the "make it not rely on a human remembering" version.)
- **Wage league-multipliers in `predict_wages.py` are static hardcoded constants**, sourced from KPMG/CIES/press benchmark reports rather than re-derived from data each run. They'll quietly go stale as wage inflation moves year over year, with no backtest or versioning. (Related to the wage-multiplier-calibration item above, but broader: consider making the calibration a repeatable, data-driven step rather than a manual constant edit.)

**Infrastructure / ops**

- **Two of three raw sources depend on a local Mac staying awake and online.** The SofaScore 6x/day extraction queue and the TM scraper (quarterly, GCP-IP-blocked so it *must* run locally) both live on launchd + `caffeinate -i -s -w $$`. If the laptop is asleep, powered off, or off-network at a firing time, that slot is just skipped — no cloud-side retry, no alert — so a backfill can silently stall for days. This is the single biggest point of non-redundancy in the whole system; worth deciding whether to accept it or migrate extraction to something always-on.
- **Scraping fragile third-party sites with no ToS/API guarantee, and it's already broken once.** The TM height/foot column-swap bug that `silver_tm_players.sql` patches around (see the "Fix TM scraper column offset bug" item above) is a real instance of "site changed layout, scraper silently miscategorized columns." There's no general schema-drift detection — an equivalent shift in SofaScore's JSON payload would silently degrade `player_stats` (e.g. all-null minutes) rather than fail loudly; the only current defense (`_PLAYER_STAT_PROBE` in `scraper_sofascore.py`) skips the write but doesn't alert anyone.
- **`rz-dbt-refresh` is triggered 3x/day by two independent schedulers** (Cloud Scheduler 06:00 Europe/Madrid + launchd 11:00/20:00 via `run_refresh_processed.sh`) with no visible mutual-exclusion lock between them. dbt's default table materialization does `CREATE OR REPLACE TABLE`; if the cloud and local triggers ever overlapped (e.g. a delayed `--wait` run runs long), two concurrent `dbt run`s hitting the same gold tables is a real, if narrow, risk. Also just wasteful of Cloud Run compute for two of the three redundant daily runs.
- **Gold tables can sit empty or stale for a full quarter** (`agg_tm_player_valuations`, `agg_rz_squad_finances`, wage tables) between TM/Capology/wage-predictor runs. No monitoring beyond the daily email digest (`send_daily_summary.py`) confirms a quarterly run actually succeeded — a failed quarterly job could go unnoticed for months.
- **`dbt-bigquery` is installed unpinned** in `pipeline/cloud-run/dbt-refresh/Dockerfile` (`pip install --no-cache-dir dbt-bigquery`, no version pin). An upstream release with breaking changes would silently start failing the nightly job on the next image rebuild.

Priority if picking where to start: identity-resolution / alias-coverage items (data quality, already possibly corrupting scouting numbers silently) and the local-machine single-point-of-failure item (most likely to cause an outright pipeline stall) first.

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
