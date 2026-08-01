#!/bin/bash
# One-time setup for GitHub Actions -> GCP authentication via Workload Identity
# Federation (WIF). Run this once, locally, as an account with IAM admin rights
# on the project. Not part of any automated pipeline -- deliberately manual.
#
# Why WIF instead of a service account JSON key: no static credential is ever
# stored in GitHub secrets. GitHub's OIDC token is exchanged for short-lived GCP
# credentials at workflow-run time, scoped to this exact repo only.
#
# What the resulting service account CAN do:
#   - Read raw/wc_2026 (bigquery.dataViewer) -- dbt bronze models source from these
#   - Read+write dev_bronze/dev_silver/dev_gold (bigquery.dataEditor) -- CI target
#   - Run BigQuery jobs (bigquery.jobUser)
#   - Trigger Cloud Build + execute the rz-dbt-refresh Cloud Run Job
#     (cloudbuild.builds.editor, run.developer) -- used only by the manual
#     dbt-deploy-prod.yml workflow
#
# What it explicitly CANNOT do: write to prod bronze/silver/gold directly. Prod
# writes only ever happen inside the rz-dbt-refresh container, under its own
# separate identity -- this SA can only ask Cloud Build/Cloud Run to run that
# container, never touch prod BigQuery tables itself. That separation is the
# actual point of this whole setup.

set -euo pipefail

PROJECT_ID="real-zaragoza-500608"
REPO="robertsoliva/Real-Zaragoza"
POOL_ID="github-pool"
PROVIDER_ID="github-provider"
SA_NAME="github-actions-dbt"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

echo "=== 1. Workload Identity Pool ==="
gcloud iam workload-identity-pools create "$POOL_ID" \
  --project="$PROJECT_ID" --location="global" \
  --display-name="GitHub Actions Pool"

echo "=== 2. OIDC Provider, restricted to $REPO only ==="
gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
  --project="$PROJECT_ID" --location="global" \
  --workload-identity-pool="$POOL_ID" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

echo "=== 3. Dedicated service account ==="
gcloud iam service-accounts create "$SA_NAME" \
  --project="$PROJECT_ID" \
  --display-name="GitHub Actions - dbt CI/CD"

echo "=== 4. Least-privilege dataset-level grants (not project-wide) ==="
for ds in raw wc_2026; do
  bq add-iam-policy-binding \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/bigquery.dataViewer" \
    "${PROJECT_ID}:${ds}"
done
for ds in dev_bronze dev_silver dev_gold; do
  bq add-iam-policy-binding \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/bigquery.dataEditor" \
    "${PROJECT_ID}:${ds}"
done

echo "=== 5. Project-level grants needed to run jobs / trigger deploys ==="
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/bigquery.jobUser"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/cloudbuild.builds.editor"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/run.developer"
# cloudbuild.builds.editor needs to act as the Cloud Build default SA to push images
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/iam.serviceAccountUser"

echo "=== 6. Allow this exact GitHub repo to impersonate the service account ==="
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPO}"

WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"

echo ""
echo "=== Done. Set these as GitHub Actions repo VARIABLES (not secrets -- not sensitive on their own): ==="
echo "  WIF_PROVIDER=${WIF_PROVIDER}"
echo "  WIF_SERVICE_ACCOUNT=${SA_EMAIL}"
echo ""
echo "Run (from repo root, gh CLI already authenticated):"
echo "  gh variable set WIF_PROVIDER --body '${WIF_PROVIDER}'"
echo "  gh variable set WIF_SERVICE_ACCOUNT --body '${SA_EMAIL}'"
