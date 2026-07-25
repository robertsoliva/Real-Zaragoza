# Build context: repo root
# gcloud builds submit . --config pipeline/cloud-run/docker/cloudbuild-transfermarkt.yaml
FROM python:3.12-slim

WORKDIR /app

COPY pipeline/cloud-run/docker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline/cloud-run/scrapers/scraper_transfermarkt.py .

CMD ["python", "scraper_transfermarkt.py"]
