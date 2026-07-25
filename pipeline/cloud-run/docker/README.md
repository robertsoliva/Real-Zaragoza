# docker/

Historical Docker configs. The active Cloud Run jobs (`rz-tm-scraper`, `rz-capology-scraper`, `rz-dbt-refresh`) have their own subdirectories under `cloud-run/`.

| File | For | Status |
|---|---|---|
| `Dockerfile.sofascore` | SofaScore Cloud Run image | Job exists, scheduler paused — GCP IPs blocked by Cloudflare |
| `requirements-sofascore.txt` | SofaScore deps | — |
| `cloudbuild-sofascore.yaml` | Cloud Build config for SofaScore image | — |

## Note on Transfermarkt multi-league

`rz-tm-scraper` uses `scraper_transfermarkt_leagues.py` and must run **locally** — GCP datacenter IPs get HTTP 202 (Cloudflare bot challenge) from Transfermarkt league index pages. See `pipeline/run_transfermarkt_leagues.sh` for local usage.
