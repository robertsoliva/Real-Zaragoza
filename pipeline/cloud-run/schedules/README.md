# schedules/

Shell runners and launchd plists that control when scrapers fire. All SofaScore runs execute locally (GCP IPs are blocked); Transfermarkt runs on Cloud Run via its own scheduler.

## Active jobs

| File | Trigger | What it does |
|---|---|---|
| `run_next_from_queue.sh` | launchd 09:00 + 18:00 | Pops next season from `sofascore_queue.txt`, runs it, removes it from queue |
| `run_daily_wc26.sh` | launchd 09:00 (WC period only) | Incremental WC 2026 scrape → `WC_26` BQ dataset |
| `run_weekly_sofascore.sh` | launchd Tuesdays 07:30 | Incremental update for all active seasons (last 14 days) |
| `run_refresh_processed.sh` | launchd 11:00 + 20:00 | Rematerialises `rz_silver` tables and `rz_gold` tables from `rz_bronze` views |

## launchd plists

| File | Schedule | Script |
|---|---|---|
| `com.realzaragoza.sofascore-9am.plist` | Daily 09:00 | `run_next_from_queue.sh` |
| `com.realzaragoza.sofascore-6pm.plist` | Daily 18:00 | `run_next_from_queue.sh` |
| `com.realzaragoza.sofascore-weekly.plist` | Tuesdays 07:30 | `run_weekly_sofascore.sh` |
| `com.realzaragoza.wc26-daily.plist` | Daily 09:00 | `run_daily_wc26.sh` |
| `com.realzaragoza.refresh-11am.plist` | Daily 11:00 | `run_refresh_processed.sh` |
| `com.realzaragoza.refresh-8pm.plist` | Daily 20:00 | `run_refresh_processed.sh` |

## The backfill queue

`sofascore_queue.txt` — priority-ordered list of seasons still to backfill. One line per season: `TOURNAMENT_ID  SEASON_ID  LABEL`. Lines with `TODO` as season ID are skipped until filled in.

`run_next_from_queue.sh` pops the first runnable line on each execution. Runs are limited to **1 season per slot** (never consecutive) to avoid Cloudflare IP bans.

## Register plists (one-time setup)

```bash
BASE=~/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/schedules

# Backfill cadence (9am + 6pm)
cp "$BASE/com.realzaragoza.sofascore-9am.plist" ~/Library/LaunchAgents/
cp "$BASE/com.realzaragoza.sofascore-6pm.plist" ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.realzaragoza.sofascore-9am.plist
launchctl load ~/Library/LaunchAgents/com.realzaragoza.sofascore-6pm.plist

# Weekly incremental
cp "$BASE/com.realzaragoza.sofascore-weekly.plist" ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.realzaragoza.sofascore-weekly.plist

# WC 2026 (only during tournament: June 11 – July 19)
cp "$BASE/com.realzaragoza.wc26-daily.plist" ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.realzaragoza.wc26-daily.plist

# Processed layer refresh (2h after each extraction slot)
cp "$BASE/com.realzaragoza.refresh-11am.plist" ~/Library/LaunchAgents/
cp "$BASE/com.realzaragoza.refresh-8pm.plist" ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.realzaragoza.refresh-11am.plist
launchctl load ~/Library/LaunchAgents/com.realzaragoza.refresh-8pm.plist
```

## Trigger a manual refresh

```bash
bash ~/Desktop/Projects/Real-Zaragoza/pipeline/cloud-run/schedules/run_refresh_processed.sh
# or via launchctl:
launchctl start com.realzaragoza.refresh-11am
```
