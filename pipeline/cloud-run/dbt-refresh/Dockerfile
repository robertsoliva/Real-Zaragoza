# Build context: repo root
# gcloud builds submit . --config pipeline/cloud-run/dbt-refresh/cloudbuild.yaml
FROM python:3.12-slim

RUN pip install --no-cache-dir dbt-bigquery

WORKDIR /app
COPY pipeline/dbt/ .

CMD ["dbt", "run", "--profiles-dir", ".", "--project-dir", "."]
