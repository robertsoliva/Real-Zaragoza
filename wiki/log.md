# Wiki change log

Append-only. One line per change set: `[YYYY-MM-DD]||One-line-summary with evidence`  
Format spec: `.claude/templates/log-entry.md` — routing rules: `.claude/skills/contribute-text/SKILL.md`

---

[2026-06-26]||Skill infrastructure added: contribute-text skill, log-entry and wiki-page templates, wiki/index.md, and wiki/log.md (initial repo setup)
[2026-06-26]||All 7 wiki pages adapted to new template conventions: TL;DR section, Model section with typed relationships, repo-relative cross-reference links throughout. wiki/README.md consolidated into wiki/index.md (single source of truth for navigation and status).
[2026-06-26]||Data pipeline architecture decided and documented: wiki/data-pipeline.md added (Cloud Scheduler → Cloud Run → Pub/Sub → Cloud Function → BQ, weekly Tuesdays); data/ and pipeline/ directory skeletons created; .gitignore expanded for credentials and raw data files; next-actions.md restructured to reflect decisions made.
[2026-06-26]||Transfermarkt scraper built and verified: pipeline/cloud-run/scraper_transfermarkt.py scrapes verein/142 /plus/1 page; 32 players extracted with full BQ-aligned schema (DOB, jersey, position, height, foot, nationality, market value, contract expiry, signing info); CSV written to data/raw/transfermarkt/.
[2026-06-26]||BQ historical strategy decided and documented: append-only rz_raw + view deduplication on (player_id, season_id) in rz_processed.squad_snapshots; SQL DDL added to wiki/data-pipeline.md; transfermarkt_squad schema updated to reflect confirmed live fields; next-actions.md updated.
[2026-06-26]||GCP infrastructure live: APIs enabled, rz_raw + rz_processed datasets created (europe-west1), rz_raw.transfermarkt_squad table created and loaded (32 rows), Pub/Sub topics rz-data-ingested + DLQ created, service account rz-pipeline created with minimum IAM roles, budget alert set at €10/month.
[2026-06-26]||Transfermarkt pipeline fully automated: Dockerfile built via Cloud Build, image pushed to Artifact Registry (rz-images/rz-scraper), Cloud Run job rz-scraper-transfermarkt deployed, Cloud Scheduler rz-weekly-ingest fires Tuesdays 06:00 CET. End-to-end test confirmed (96 rows in BQ across 3 runs).
[2026-06-26]||FotMob scraper built and smoke-tested: pipeline/cloud-run/scraper_fotmob.py covers LaLiga2 (leagueId=893055) 2024-25 full season via date-iteration; BQ tables fotmob_matches + fotmob_player_match_stats + fotmob_shots created in rz_raw; Dockerfile.fotmob uses Playwright/Chromium base image. Confirmed: Zaragoza was in LaLiga2 in 2024-25 (not 1RFEF); 1RFEF has lower-coverage only (no player stats in FotMob). Cloud Run deployment pending.
