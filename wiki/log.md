# Wiki change log

Append-only. One line per change set: `[YYYY-MM-DD]||One-line-summary with evidence`  
Format spec: `.claude/templates/log-entry.md` — routing rules: `.claude/skills/contribute-text/SKILL.md`

---

[2026-06-26]||Skill infrastructure added: contribute-text skill, log-entry and wiki-page templates, wiki/index.md, and wiki/log.md (initial repo setup)
[2026-06-26]||All 7 wiki pages adapted to new template conventions: TL;DR section, Model section with typed relationships, repo-relative cross-reference links throughout. wiki/README.md consolidated into wiki/index.md (single source of truth for navigation and status).
[2026-06-26]||Data pipeline architecture decided and documented: wiki/data-pipeline.md added (Cloud Scheduler → Cloud Run → Pub/Sub → Cloud Function → BQ, weekly Tuesdays); data/ and pipeline/ directory skeletons created; .gitignore expanded for credentials and raw data files; next-actions.md restructured to reflect decisions made.
[2026-06-26]||Transfermarkt scraper built and verified: pipeline/cloud-run/scraper_transfermarkt.py scrapes verein/142 /plus/1 page; 32 players extracted with full BQ-aligned schema (DOB, jersey, position, height, foot, nationality, market value, contract expiry, signing info); CSV written to data/raw/transfermarkt/.
[2026-06-26]||BQ historical strategy decided and documented: append-only rz_raw + view deduplication on (player_id, season_id) in rz_processed.squad_snapshots; SQL DDL added to wiki/data-pipeline.md; transfermarkt_squad schema updated to reflect confirmed live fields; next-actions.md updated.
