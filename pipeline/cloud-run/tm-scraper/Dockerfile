# Build context: repo root
# gcloud builds submit . --config pipeline/cloud-run/tm-scraper/cloudbuild.yaml
FROM python:3.12-slim
WORKDIR /app
COPY pipeline/cloud-run/tm-scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pipeline/cloud-run/scrapers/scraper_transfermarkt_leagues.py .
CMD ["python", "scraper_transfermarkt_leagues.py"]
