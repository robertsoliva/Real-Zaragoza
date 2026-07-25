#!/bin/bash
# Triggers rz-dbt-refresh Cloud Run Job on GCP as a mid-day supplemental refresh.
# Fires at 11:00 and 20:00 via launchd (see com.realzaragoza.refresh-*.plist).
# Primary refresh also runs at 06:00 Madrid time via Cloud Scheduler.

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

set -euo pipefail

LOG="/tmp/rz_refresh_processed_$(date +%Y%m%d_%H%M%S).log"
REGION="europe-west1"
PROJECT="real-zaragoza-500608"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Triggering rz-dbt-refresh" | tee "$LOG"

gcloud run jobs execute rz-dbt-refresh \
    --region="$REGION" --project="$PROJECT" --wait \
    >> "$LOG" 2>&1 \
    && echo "[$(date '+%Y-%m-%d %H:%M:%S')] rz-dbt-refresh done" | tee -a "$LOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Refresh complete. Log: $LOG"
