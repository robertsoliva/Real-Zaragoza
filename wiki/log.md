# Wiki change log

Append-only. One line per change set: `[YYYY-MM-DD]||One-line-summary with evidence`  
Format spec: `.claude/templates/log-entry.md` — routing rules: `.claude/skills/contribute-text/SKILL.md`

---

[2026-06-26]||Skill infrastructure added: contribute-text skill, log-entry and wiki-page templates, wiki/index.md, and wiki/log.md (initial repo setup)
[2026-06-26]||All 7 wiki pages adapted to new template conventions: TL;DR section, Model section with typed relationships, repo-relative cross-reference links throughout. wiki/README.md consolidated into wiki/index.md (single source of truth for navigation and status).
[2026-06-26]||Data pipeline architecture decided and documented: wiki/data-pipeline.md added (Cloud Scheduler → Cloud Run → Pub/Sub → Cloud Function → BQ, weekly Tuesdays); data/ and pipeline/ directory skeletons created; .gitignore expanded for credentials and raw data files; next-actions.md restructured to reflect decisions made.
