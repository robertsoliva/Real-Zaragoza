# docker/

Container definitions for Cloud Run deployments. **Only Transfermarkt runs on Cloud Run.** SofaScore's Cloud Run job (`rz-scraper-sofascore`) exists but its scheduler is paused — GCP datacenter IPs are blocked by SofaScore's Cloudflare layer.

| File | For |
|---|---|
| `Dockerfile` | Transfermarkt Zaragoza-only scraper (`rz-scraper` Cloud Run Job) |
| `Dockerfile.sofascore` | SofaScore scraper (built, scheduler paused) |
| `requirements.txt` | Transfermarkt deps |
| `requirements-sofascore.txt` | SofaScore deps (`curl_cffi`, `pandas`, `google-cloud-bigquery`) |
| `cloudbuild-sofascore.yaml` | Cloud Build config for SofaScore image |

## Rebuild SofaScore image

```bash
cd pipeline/cloud-run/docker
gcloud builds submit . --config cloudbuild-sofascore.yaml
```
