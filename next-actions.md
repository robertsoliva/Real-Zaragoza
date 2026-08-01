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

- **Identity crosswalk (SofaScore player_id ↔ TM player_id) — investigated 2026-08-01, shelved as unclear ROI.** Built `pipeline/scripts/build_team_id_map.py` (extends `club_name_aliases.csv` with `sofascore_team_id`/`tm_club_id` — 100%/99.7% resolved) and `pipeline/scripts/build_player_id_map.py` (produces `pipeline/dbt/seeds/player_id_map.csv`, a static `sofascore_player_id ↔ tm_player_id` map using club-affiliation as a matching signal, not a join key, so transferred players stay matched). **Neither is wired into any model** — both scripts ran and their output sits in the repo, but the seeds haven't even been `dbt seed`-loaded into BigQuery (local dbt is broken, see infra note below), so this has zero effect on production tables right now.
  Measured findings (see conversation 2026-08-01 for full methodology) before shelving:
  - Restricted to scouting-relevant players (≥450 min in a season), the trusted tier (`club_bridge_auto`, 8,660 players / 45.7% of all SofaScore players) rescues only **551 net-new matches out of 10,811 relevant players (5.1%)** beyond what the existing `LOWER(TRIM(name))` join in `agg_scouting_player_season` already finds (56.4% baseline).
  - **Zero disagreements** between the crosswalk and the existing name+club join wherever both had an opinion (7,406 overlapping matches, 100% agreement) — so the existing join isn't silently corrupting matches for the population this crosswalk could check; the crosswalk's only value is filling gaps, not fixing wrong answers.
  - Of the 4,718 still-unmatched relevant players: only 31.4% (1,481) are a genuinely fixable matching problem (a plausible name candidate exists at a bridged club, just below the auto-accept confidence bar — would need manual review, sampling suggests ~40-60% of these are correct once eyeballed). The other 68.6% are a **TM data-coverage gap, not a matching problem**: either the club has no TM squad data at all (26.5%) or TM's snapshot for that club simply doesn't list the player (42.1%). No identity-matching technique fixes that — the actual lever is TM scrape completeness/cadence (quarterly single-snapshot scraping will always miss players who transferred between snapshots).
  - **If picked back up:** the cheap, zero-risk move is wiring in just `club_bridge_auto` (551 free matches, no observed downside) — the bigger question worth answering first is whether investing in TM scrape frequency/completeness would do more for coverage than any further identity-matching work.
- **`silver_tm_players` dedups player+club+season, but `silver_bqml_wages` dedups by player name only, ignoring club** (`pipeline/dbt/models/silver/silver_bqml_wages.sql` — the SQL comment admits this is a deliberate workaround for players who transferred between the TM scrape and the season being scored). Two same-named players anywhere across all 25 leagues will merge into one wage prediction. Conscious tradeoff at the time, but a real correctness gap. The `player_id_map.csv` seed above (currently unwired) would fix this cleanly if the identity-crosswalk item is ever picked back up — dedupe/join on `tm_player_id` instead of name.
- **`club_name_aliases.csv` (`pipeline/dbt/seeds/club_name_aliases.csv`) is a hand-maintained seed with no coverage check — DONE 2026-08-01.** Every promotion/relegation or new club across the 25 pipeline leagues needs a manual alias row added, or `gold.agg_scouting_player_season` silently loses that club's market-value/wage join. Now has `sofascore_team_id`/`tm_club_id` columns (100%/99.7% resolved) from the crosswalk investigation, usable independent of whether the player-level crosswalk gets revisited. **Monitoring added**: `pipeline/cloud-run/schedules/send_daily_summary.py::check_tm_match_quality()` compares each league's current TM-match % (players ≥450 min in `gold.agg_scouting_player_season`) against a captured baseline (`pipeline/cloud-run/schedules/tm_match_baseline.json`, captured 2026-08-01) and flags any league that regresses more than 5pp below its baseline in the daily digest email. Fails soft (logs a skip note in the email) if BQ creds aren't available rather than breaking the whole digest. Re-capture the baseline deliberately after any change expected to *improve* match rate — don't let it silently ratchet down after a real regression.
- **No visible dbt tests — audited 2026-08-01, mostly a false alarm, 3 real gaps fixed.** Turned out `gold/schema.yml` and `silver/schema.yml` already had solid `unique_combination_of_columns`/`not_null`/`accepted_values` coverage on most models. Found and fixed 3 genuine gaps: `silver_capology_wages` and `agg_tm_player_valuations` had no grain-uniqueness test despite documented multi-column grains; `silver_bqml_wages.player_name` (the grain key powering the wage COALESCE fallback in `agg_scouting_player_season`) had no test at all. All three now have `unique`/`unique_combination_of_columns` tests in their respective `schema.yml`.
- **Cluster labels in `gold.agg_player_profiles` are hand-assigned and can silently desync from the model.** The model's own SQL comment warns that `CENTROID_ID` ordering can shift between retrains, but the `CASE CENTROID_ID WHEN 1 THEN 'Dominant Aerial CB' ...` label mapping isn't re-verified automatically. Retraining `ml.player_cluster_*` without also re-checking `ML.CENTROIDS` and updating labels produces confidently-wrong archetype names with no error. (Already noted as a re-verify step in the sporting-analysis retrain checklist above — this entry is the "make it not rely on a human remembering" version. Not yet addressed — still open.)
- **Wage league-multipliers in `predict_wages.py` are static hardcoded constants — staleness warning added 2026-08-01.** Sourced from KPMG/CIES/press benchmark reports rather than re-derived from data each run, so they'll quietly go stale as wage inflation moves year over year. Added `MULTIPLIER_LAST_REVIEWED` date constant + a `log.warning()` that fires on every `rz-wage-predictor` run once >100 days (~1 quarter) have elapsed since that date — visible in Cloud Run job logs each quarterly run. Doesn't recalibrate anything automatically (still a manual constant edit), just makes the staleness visible instead of silent. Bump `MULTIPLIER_LAST_REVIEWED` whenever the constants are actually re-derived.

**Infrastructure / ops**

- **Two of three raw sources depend on a local Mac staying awake and online.** The SofaScore 6x/day extraction queue and the TM scraper (quarterly, GCP-IP-blocked so it *must* run locally) both live on launchd + `caffeinate -i -s -w $$`. If the laptop is asleep, powered off, or off-network at a firing time, that slot is just skipped — no cloud-side retry, no alert — so a backfill can silently stall for days. This is the single biggest point of non-redundancy in the whole system; worth deciding whether to accept it or migrate extraction to something always-on.
- **Scraping fragile third-party sites with no ToS/API guarantee, and it's already broken once.** The TM height/foot column-swap bug that `silver_tm_players.sql` patches around (see the "Fix TM scraper column offset bug" item above) is a real instance of "site changed layout, scraper silently miscategorized columns." There's no general schema-drift detection — an equivalent shift in SofaScore's JSON payload would silently degrade `player_stats` (e.g. all-null minutes) rather than fail loudly; the only current defense (`_PLAYER_STAT_PROBE` in `scraper_sofascore.py`) skips the write but doesn't alert anyone.
- **`rz-dbt-refresh` is triggered 3x/day by two independent schedulers** (Cloud Scheduler 06:00 Europe/Madrid + launchd 11:00/20:00 via `run_refresh_processed.sh`) with no visible mutual-exclusion lock between them. dbt's default table materialization does `CREATE OR REPLACE TABLE`; if the cloud and local triggers ever overlapped (e.g. a delayed `--wait` run runs long), two concurrent `dbt run`s hitting the same gold tables is a real, if narrow, risk. Also just wasteful of Cloud Run compute for two of the three redundant daily runs.
- **Gold tables can sit empty or stale for a full quarter** (`agg_tm_player_valuations`, `agg_rz_squad_finances`, wage tables) between TM/Capology/wage-predictor runs. No monitoring beyond the daily email digest (`send_daily_summary.py`) confirms a quarterly run actually succeeded — a failed quarterly job could go unnoticed for months.
- **`dbt-bigquery` is installed unpinned** in `pipeline/cloud-run/dbt-refresh/Dockerfile` (`pip install --no-cache-dir dbt-bigquery`, no version pin). An upstream release with breaking changes would silently start failing the nightly job on the next image rebuild.
- **`league_name` mislabeling bug (found 2026-08-01, fixed in code, not yet deployed).** `scraper_sofascore.py`'s `LEAGUE_NAMES` dict and the `bronze_matches`/`bronze_player_stats`/`bronze_team_stats`/`bronze_shots` CASE patches only covered tournament_id 16/35/44 — Premier League (17), La Liga (8), Serie A (23), and Ligue 1 (34) fell through to the `tournament_{id}` fallback. Confirmed live: `silver.matches` had rows with `league_name='tournament_17'`. Fixed the scraper dict and all 4 bronze CASE statements (working tree, uncommitted). **Needs deployment**: local `dbt` is broken (see below), so this hasn't been applied to production `bronze`/`silver`/`gold` yet — needs either a working local dbt env to run `dbt run`, or a Cloud Run image rebuild (`gcloud builds submit . --config pipeline/cloud-run/dbt-refresh/cloudbuild.yaml`) + job execution.
- **Local `dbt` environment is broken.** `pip install dbt-bigquery` succeeds (dbt-core 1.12.0, bigquery plugin 1.12.0) and `dbt --version` works, but every real command (`dbt deps`, `dbt run`) gets killed (exit 137) instantly, even with the sandbox disabled — looks like a native crash from a dependency conflict pip flagged during install (protobuf got bumped to 6.33.6, several other conda packages expect <5). This blocks any local dbt validation/ad-hoc runs (the pipeline normally only runs dbt inside the `rz-dbt-refresh` Docker container, so this hasn't mattered before now). Worth a clean venv instead of installing into the shared anaconda environment next time this is needed.

Priority if picking where to start: the local-machine single-point-of-failure item (most likely to cause an outright pipeline stall) and deploying the `league_name` fix above (quick, unambiguous, already coded) first. Identity-crosswalk work is shelved for now — see finding above.

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
