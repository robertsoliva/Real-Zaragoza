# Build context: repo root
# gcloud builds submit . --config pipeline/cloud-run/dbt-refresh/cloudbuild.yaml
FROM python:3.12-slim

# Pinned: this image is only rebuilt on demand (not on a schedule), so an unpinned
# install would silently pick up a breaking dbt-bigquery release on the next rebuild.
# Bump deliberately, not automatically.
RUN pip install --no-cache-dir dbt-bigquery==1.12.0

WORKDIR /app
COPY pipeline/dbt/ .
COPY pipeline/cloud-run/dbt-refresh/run_with_lock.py .

# run_with_lock.py wraps `dbt deps && dbt seed && dbt run` with a BigQuery-backed
# mutual-exclusion lock (ops.pipeline_locks) -- this job is triggered by two
# independent schedulers (Cloud Scheduler + launchd) with no coordination between
# them, so this stops overlapping runs from both CREATE OR REPLACE TABLE-ing the
# same gold tables. Fails open (runs dbt anyway) if the lock check itself errors.
#
# ENTRYPOINT/CMD split preserved so `gcloud run jobs execute --args=...` can still
# override just the final `dbt run` args for one-off executions (e.g. the
# player_clustering manual retrain) without touching the default daily command.
# Default CMD args exclude player_clustering; pass
# --args="--select,tag:player_clustering" to build just that.
ENTRYPOINT ["python3", "run_with_lock.py"]
CMD ["--exclude", "tag:player_clustering"]
