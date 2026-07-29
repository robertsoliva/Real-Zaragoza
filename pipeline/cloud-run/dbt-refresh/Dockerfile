# Build context: repo root
# gcloud builds submit . --config pipeline/cloud-run/dbt-refresh/cloudbuild.yaml
FROM python:3.12-slim

RUN pip install --no-cache-dir dbt-bigquery

WORKDIR /app
COPY pipeline/dbt/ .

# ENTRYPOINT/CMD split so `gcloud run jobs execute --args=...` can override just the
# final `dbt run` args for one-off executions (e.g. the player_clustering manual
# retrain) without touching the default daily command. Default CMD args exclude
# player_clustering; pass --args="--select,tag:player_clustering" to build just that.
ENTRYPOINT ["/bin/sh", "-c", "dbt deps --profiles-dir . --project-dir . && dbt seed --profiles-dir . --project-dir . && dbt run --profiles-dir . --project-dir . \"$@\"", "--"]
CMD ["--exclude", "tag:player_clustering"]
