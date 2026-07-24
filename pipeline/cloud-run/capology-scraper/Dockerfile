# Build context: repo root
# gcloud builds submit . --config pipeline/cloud-run/capology-scraper/cloudbuild.yaml
FROM python:3.12-slim
WORKDIR /app
COPY pipeline/cloud-run/capology-scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pipeline/cloud-run/scrapers/scraper_capology.py .
CMD ["python", "scraper_capology.py"]
