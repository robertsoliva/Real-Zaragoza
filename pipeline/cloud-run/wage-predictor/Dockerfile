FROM python:3.12-slim

RUN pip install --no-cache-dir google-cloud-bigquery==3.25.0

WORKDIR /app
COPY predict_wages.py .

CMD ["python3", "predict_wages.py"]
