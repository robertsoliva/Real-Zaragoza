# scrapers/

Python source for all data extractors. Run directly; Cloud Run is not used for SofaScore (GCP IPs are blocked by Cloudflare).

| File | What it does |
|---|---|
| `scraper_sofascore.py` | Main extractor: matches, player/team stats, shots → `rz_raw.*` (or `WC_26.*`). Controlled via env vars (`TOURNAMENT_ID`, `SEASON_ID`, `INCREMENTAL`, `BQ_DATASET`). |
| `scraper_transfermarkt.py` | Squad + market values → `rz_raw.transfermarkt_squad`. Runs on Cloud Run weekly. |
| `seasons_lookup.py` | Helper: given a tournament ID, prints all available season IDs. Run this when adding a new league. |

## Quick usage

```bash
# Run next queued season (preferred — use the queue)
bash ../schedules/run_next_from_queue.sh

# One-off manual run
GCP_PROJECT_ID=real-zaragoza-500608 TOURNAMENT_ID=54 SEASON_ID=77558 \
  python3 scraper_sofascore.py

# Incremental (last 14 days)
GCP_PROJECT_ID=real-zaragoza-500608 TOURNAMENT_ID=54 SEASON_ID=77558 INCREMENTAL=true \
  python3 scraper_sofascore.py

# Look up season IDs for new leagues
python3 seasons_lookup.py 17 52 57 45 55
```
