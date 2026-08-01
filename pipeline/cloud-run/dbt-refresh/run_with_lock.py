"""
Entrypoint wrapper for the rz-dbt-refresh Cloud Run Job.

Why: rz-dbt-refresh is triggered 3x/day by two independent schedulers (Cloud
Scheduler 06:00 + launchd 11:00/20:00) with no coordination between them. dbt's
table materializations do CREATE OR REPLACE TABLE, so two overlapping `dbt run`
executions hitting the same gold tables is a real (if narrow) risk. This wrapper
takes a lock in BigQuery (ops.pipeline_locks) before running dbt, and always
releases it afterward, regardless of trigger source.

Design choices:
  - BigQuery, not GCS/Firestore: google-cloud-bigquery is already a transitive
    dependency of dbt-bigquery, so no new dependency in the image.
  - Not a true atomic compare-and-swap (BigQuery isn't built for row-level
    locking) -- there's a narrow race window if two executions check-then-insert
    within milliseconds of each other. Acceptable here: the real-world overlap
    scenario is "a run is still going when the next scheduled trigger fires"
    (minutes apart), not two literally-simultaneous triggers.
  - FAILS OPEN: if the lock check/acquire itself errors for any reason (BQ
    permission issue, network blip, ops dataset not existing), we log and run
    dbt anyway. The narrow concurrency risk this guards against is much less
    bad than silently breaking the only thing that populates bronze/silver/gold.
  - Stale locks (a previous execution crashed without releasing) expire after
    STALE_LOCK_MINUTES so a bad run doesn't permanently wedge future refreshes.
"""

import logging
import os
import subprocess
import sys
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("run_with_lock")

PROJECT = os.environ.get("GCP_PROJECT_ID", "real-zaragoza-500608")
JOB_NAME = "rz-dbt-refresh"
STALE_LOCK_MINUTES = 30
LOCKED_BY = os.environ.get("CLOUD_RUN_EXECUTION", "local")


def try_acquire_lock(client) -> bool:
    """Return True if the lock was acquired (or the check failed open)."""
    try:
        from google.cloud import bigquery

        client.query(f"""
            CREATE TABLE IF NOT EXISTS `{PROJECT}.ops.pipeline_locks` (
              job_name STRING NOT NULL, locked_at TIMESTAMP NOT NULL, locked_by STRING
            )
        """).result()

        check = client.query(f"""
            SELECT locked_at, locked_by FROM `{PROJECT}.ops.pipeline_locks`
            WHERE job_name = @job_name
              AND locked_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {STALE_LOCK_MINUTES} MINUTE)
        """, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("job_name", "STRING", JOB_NAME),
        ])).result()
        rows = list(check)
        if rows:
            log.warning(
                "Lock already held by %r since %s (< %d min ago) -- another %s "
                "execution is likely still running. Exiting without running dbt.",
                rows[0].locked_by, rows[0].locked_at, STALE_LOCK_MINUTES, JOB_NAME,
            )
            return False

        # Clear any stale lock row, then insert ours. Not atomic against a
        # concurrent acquirer (see module docstring) -- acceptable tradeoff here.
        client.query(f"""
            DELETE FROM `{PROJECT}.ops.pipeline_locks` WHERE job_name = @job_name
        """, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("job_name", "STRING", JOB_NAME),
        ])).result()
        client.query(f"""
            INSERT INTO `{PROJECT}.ops.pipeline_locks` (job_name, locked_at, locked_by)
            VALUES (@job_name, CURRENT_TIMESTAMP(), @locked_by)
        """, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("job_name", "STRING", JOB_NAME),
            bigquery.ScalarQueryParameter("locked_by", "STRING", LOCKED_BY),
        ])).result()
        log.info("Lock acquired (locked_by=%s)", LOCKED_BY)
        return True
    except Exception as e:
        log.warning("Lock check/acquire failed (%s) -- failing open, running dbt anyway.", e)
        return True


def release_lock(client) -> None:
    try:
        from google.cloud import bigquery
        client.query(f"""
            DELETE FROM `{PROJECT}.ops.pipeline_locks`
            WHERE job_name = @job_name AND locked_by = @locked_by
        """, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("job_name", "STRING", JOB_NAME),
            bigquery.ScalarQueryParameter("locked_by", "STRING", LOCKED_BY),
        ])).result()
        log.info("Lock released")
    except Exception as e:
        log.warning("Lock release failed (%s) -- it will self-expire after %d min.", e, STALE_LOCK_MINUTES)


def run_dbt(extra_args: list[str]) -> int:
    # --target prod is explicit and non-negotiable here: profiles.yml defaults to
    # `dev` for safety (so a bare local `dbt run` never touches production), and
    # this container is the one thing that's actually supposed to write to prod.
    steps = [
        ["dbt", "deps", "--profiles-dir", ".", "--project-dir", "."],
        ["dbt", "seed", "--profiles-dir", ".", "--project-dir", ".", "--target", "prod"],
        ["dbt", "run", "--profiles-dir", ".", "--project-dir", ".", "--target", "prod"] + extra_args,
    ]
    for cmd in steps:
        log.info("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd)
        if result.returncode != 0:
            return result.returncode
    return 0


def main() -> None:
    extra_args = sys.argv[1:]
    client = None
    acquired = True
    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=PROJECT)
        acquired = try_acquire_lock(client)
    except Exception as e:
        log.warning("Could not initialize BigQuery client for locking (%s) -- failing open.", e)

    if not acquired:
        sys.exit(0)

    exit_code = 1
    try:
        exit_code = run_dbt(extra_args)
    finally:
        if client is not None:
            release_lock(client)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
