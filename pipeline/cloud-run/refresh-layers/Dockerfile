# Build context: repo root
# gcloud builds submit . --config pipeline/cloud-run/refresh-layers/cloudbuild.yaml
FROM python:3.12-slim

WORKDIR /app

COPY pipeline/cloud-run/refresh-layers/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline/cloud-run/refresh-layers/main.py .
COPY pipeline/sql/ sql/

CMD ["python", "main.py"]
