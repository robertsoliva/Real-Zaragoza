#!/bin/bash
# One-time setup: Cloud Monitoring email alerts for Cloud Run Job failures.
# Run manually: bash pipeline/cloud-run/setup_monitoring.sh
#
# Creates:
#   - 1 email notification channel (robertsolivamachin@gmail.com)
#   - 3 log-based alert policies: rz-dbt-refresh, rz-capology-scraper, rz-tm-scraper
#
# Re-running creates duplicate policies — check first:
#   gcloud monitoring policies list --project=real-zaragoza-500608

set -euo pipefail

PROJECT="real-zaragoza-500608"
EMAIL="robertsolivamachin@gmail.com"
REGION="europe-west1"
TOKEN=$(gcloud auth print-access-token)
BASE="https://monitoring.googleapis.com/v3/projects/${PROJECT}"

echo "=== Cloud Monitoring alert setup: $(date) ==="

# ── 1. Create email notification channel ────────────────────────────────────
echo ""
echo "Creating notification channel → ${EMAIL}"
CHANNEL_RESPONSE=$(curl -s -X POST \
  "${BASE}/notificationChannels" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"email\",
    \"displayName\": \"rz-alerts-email\",
    \"labels\": {\"email_address\": \"${EMAIL}\"},
    \"enabled\": true
  }")

CHANNEL_NAME=$(echo "$CHANNEL_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name',''))")
if [[ -z "$CHANNEL_NAME" ]]; then
  echo "ERROR: failed to create notification channel"
  echo "$CHANNEL_RESPONSE"
  exit 1
fi
echo "  Created: ${CHANNEL_NAME}"

# ── 2. Create alert policy for a given Cloud Run Job ────────────────────────
create_alert() {
  local job_name=$1
  local display_name="Cloud Run Job Failed: ${job_name}"
  local filter="resource.type=\"cloud_run_job\" resource.labels.job_name=\"${job_name}\" severity>=\"ERROR\""

  echo ""
  echo "Creating alert policy: ${display_name}"
  RESPONSE=$(curl -s -X POST \
    "${BASE}/alertPolicies" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"displayName\": \"${display_name}\",
      \"conditions\": [{
        \"displayName\": \"Job failure log match\",
        \"conditionMatchedLog\": {
          \"filter\": \"${filter}\"
        }
      }],
      \"alertStrategy\": {
        \"notificationRateLimit\": { \"period\": \"3600s\" },
        \"autoClose\": \"604800s\"
      },
      \"combiner\": \"OR\",
      \"enabled\": true,
      \"notificationChannels\": [\"${CHANNEL_NAME}\"],
      \"documentation\": {
        \"content\": \"Cloud Run Job **${job_name}** logged an error. Check Cloud Logging: https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_job%22%20resource.labels.job_name%3D%22${job_name}%22;project=${PROJECT}\",
        \"mimeType\": \"text/markdown\"
      }
    }")

  POLICY_NAME=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name',''))")
  if [[ -z "$POLICY_NAME" ]]; then
    echo "  ERROR creating policy for ${job_name}"
    echo "  $RESPONSE"
  else
    echo "  Created: ${POLICY_NAME}"
  fi
}

# Alert on the two jobs that actually run from GCP
create_alert "rz-dbt-refresh"
create_alert "rz-capology-scraper"
# rz-tm-scraper runs locally (Cloudflare blocks GCP IPs) — still alert if
# someone accidentally triggers it from Cloud Run and it errors
create_alert "rz-tm-scraper"

echo ""
echo "=== Setup complete ==="
echo "    View policies: https://console.cloud.google.com/monitoring/alerting?project=${PROJECT}"
echo "    Email channel must be verified — check ${EMAIL} inbox for Google confirmation."
