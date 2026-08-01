# schedules/

Shell runners and launchd plists that control when scrapers and refresh jobs fire. All SofaScore runs execute locally (GCP IPs are blocked); Transfermarkt and Capology run on Cloud Run via their own schedulers.

## Active jobs

| File | Trigger | What it does |
|---|---|---|
| `run_next_from_queue.sh` | launchd 6×/day (00:00, 04:00, 08:00, 12:00, 16:00, 20:00) | Pops next season from `sofascore_queue.txt`, runs it, removes it, runs GCS backup |
| `run_weekly_sofascore.sh` | launchd Tuesdays 07:30 | Incremental update for all active seasons (last 14 days) |
| `run_refresh_processed.sh` | launchd 11:00 + 20:00 | Triggers `rz-dbt-refresh` Cloud Run Job. Fires alongside Cloud Scheduler's 06:00 trigger with no coordination between them — safe since 2026-08-01: the job itself (`pipeline/cloud-run/dbt-refresh/run_with_lock.py`) takes a BigQuery-backed lock (`ops.pipeline_locks`) before running dbt, regardless of which trigger fired it. |
| `backup_raw_to_gcs.sh` | Called by `run_next_from_queue.sh` | Exports all raw BQ tables to `gs://rz-raw-backups/YYYY-MM-DD/` as Parquet (includes `transfermarkt_players`/`capology_wages`/`bqml_wage_predictions`, not just SofaScore) |
| `run_daily_wc26.sh` | *(archived — WC 2026 complete)* | WC incremental scrape; plists unloaded |
| `send_daily_summary.py` | `com.realzaragoza.daily-email.plist` | Daily pipeline summary email. Also checks (added 2026-08-01): per-league TM-match-rate regression vs. `tm_match_baseline.json` (>5pp drop flagged), and quarterly-job freshness for TM/Capology/wage-predictor (>100 days since last update flagged). Both fail soft — a check error is noted in the email, never blocks it from sending. **Open issue**: the email itself reportedly needs re-authenticating daily due to a permissions problem (root cause not yet identified — Gmail app-password or local `gcloud`/BQ token expiry are the likely suspects) — worth fixing before relying on these alerts long-term. |

## launchd plists

| File | Schedule | Script |
|---|---|---|
| `com.realzaragoza.sofascore-midnight.plist` | Daily 00:00 | `run_next_from_queue.sh` |
| `com.realzaragoza.sofascore-4am.plist` | Daily 04:00 | `run_next_from_queue.sh` |
| `com.realzaragoza.sofascore-8am.plist` | Daily 08:00 | `run_next_from_queue.sh` |
| `com.realzaragoza.sofascore-noon.plist` | Daily 12:00 | `run_next_from_queue.sh` |
| `com.realzaragoza.sofascore-4pm.plist` | Daily 16:00 | `run_next_from_queue.sh` |
| `com.realzaragoza.sofascore-8pm.plist` | Daily 20:00 | `run_next_from_queue.sh` |
| `com.realzaragoza.sofascore-weekly.plist` | Tuesdays 07:30 | `run_weekly_sofascore.sh` |
| `com.realzaragoza.refresh-11am.plist` | Daily 11:00 | `run_refresh_processed.sh` |
| `com.realzaragoza.refresh-8pm.plist` | Daily 20:00 | `run_refresh_processed.sh` |
| `com.realzaragoza.daily-email.plist` | Daily | `send_daily_summary.py` |
| `com.realzaragoza.wc26-daily.plist` | *(archived)* | `run_daily_wc26.sh` — tournament over |

## The backfill queue

`sofascore_queue.txt` — priority-ordered list of seasons to backfill. One line per season: `TOURNAMENT_ID  SEASON_ID  LABEL`. Lines with `TODO` as season ID are skipped.

`run_next_from_queue.sh` pops the first runnable line on each execution. **Never run 2+ consecutive seasons — triggers 24h Cloudflare IP ban.** One season per 4-hour slot.

## Register plists (one-time setup)

```bash
BASE=~/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/schedules

for plist in \
    com.realzaragoza.sofascore-midnight \
    com.realzaragoza.sofascore-4am \
    com.realzaragoza.sofascore-8am \
    com.realzaragoza.sofascore-noon \
    com.realzaragoza.sofascore-4pm \
    com.realzaragoza.sofascore-8pm \
    com.realzaragoza.sofascore-weekly \
    com.realzaragoza.refresh-11am \
    com.realzaragoza.refresh-8pm \
    com.realzaragoza.daily-email; do
    cp "$BASE/$plist.plist" ~/Library/LaunchAgents/
    launchctl load ~/Library/LaunchAgents/$plist.plist
done
```

## GCS backup

After each SofaScore extraction, `backup_raw_to_gcs.sh` exports all 11 raw BQ tables to `gs://rz-raw-backups/YYYY-MM-DD/`. Same-day runs overwrite the same path — one snapshot per calendar day.

To restore a table from backup:
```bash
bq load --source_format=PARQUET \
    real-zaragoza-500608:raw.sofascore_matches \
    'gs://rz-raw-backups/2026-07-25/raw/sofascore_matches/*.parquet'
```
