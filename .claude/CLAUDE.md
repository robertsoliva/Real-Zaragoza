# Real-Zaragoza repo — instructions for Claude

## README.md

Keep it short and accurate. Updated 2026-07-07 to reflect launchd pipeline and 16-league coverage; 4 more leagues in queue as of 2026-07-22 (Eredivisie, Belgian Pro League, Liga Portugal, 2. Bundesliga). Don't expand it into a full technical reference — that lives in `wiki/architecture.md`.

## What this repo is

An ongoing analysis project on Real Zaragoza CF, covering both sporting (players, results, stats) and institutional (ownership, management, structure) aspects. Two kinds of content live here, and they should not be mixed:

- **`wiki/`** — what we *know*. Karpathy-style LLM wiki: small, atomic markdown pages, one topic each, written/maintained primarily by Claude. Each page should be sourced and dated. Treat it as a living reference, not a one-off writeup — when a fact changes (a transfer, a coaching change, a relegation), edit the page in place rather than leaving stale info next to new info.
- **`next-actions.md`** (repo root) — what we plan to *build*. Backlog of future data pulls, features, and ideas. Not part of the wiki.

## Wiki conventions

- One topic per file, atomic — don't let pages sprawl into catch-alls.
- Every page starts with a `> **Status:**` line noting it's a living document and the last-updated date.
- Every factual claim should be traceable to a source — end each page with a `## Sources` section of markdown links.
- If a fact is uncertain, recently changed, or actively in flux (e.g. an ongoing boardroom restructuring), say so explicitly in an "Open items" section rather than stating it as settled. Don't guess at facts that are time-sensitive (current manager, current owners, current league position) — verify via web search before writing, since these change frequently and may be newer than training knowledge.
- Prefer Spanish-language sources for Aragonese/club-specific news (more coverage, often first to report), but write the wiki content itself in English unless told otherwise.
- **Sources of truth:** [realzaragoza.com](https://www.realzaragoza.com/) (browse it, don't just hit the homepage) and the [Spanish Wikipedia article](https://es.wikipedia.org/wiki/Real_Zaragoza) outrank every other source. If day-to-day press contradicts these two, these two win — but still note the discrepancy rather than silently dropping it, since the official site/Wikipedia can also lag breaking news (e.g. an org chart not yet updated after an announced departure).

## Data platform

The pipeline is live. SofaScore match/player/team/shot data and Transfermarkt squad data are loaded into BigQuery (`real-zaragoza-500608.rz_raw`). Raw data lives in `data/` and BQ — not in `wiki/`. Wiki pages may summarise or reference data findings but should never contain raw tables.

Active leagues: LaLiga2 (54), 1RFEF (17073), Serie B (53), Ligue 2 (182), Romanian SuperLiga (152), J1 League (196), Turkish Süper Lig (52), Norwegian Eliteserien (20), Austrian Bundesliga (45), Korean K League 1 (410), Brasileirao Serie B (390), Mozzart Bet Superliga (210), MLS (242), Allsvenskan (40), Eerste Divisie (131), Moldovan Super Liga (685). **In queue / backfilling (added 2026-07-22):** Eredivisie (37), Belgian Pro League (38), Liga Portugal (238), 2. Bundesliga (35) — IDs confirmed, data loading via launchd cadence. WC 2026 in separate dataset `WC_26` (tournament_id=16, season_id=58210). Season IDs and full backfill queue in `.claude/agents/data-engineer/AGENT.md`.

**Processed layers:** Raw data in `rz_raw`/`WC_26`. Processed data in three datasets: `rz_bronze` (views, union + normalise), `rz_silver` (tables, dedup + fixes), `rz_gold` (tables, aggregated). SQL definitions in `pipeline/sql/{bronze,silver,gold}/`. Always query `rz_silver` or `rz_gold` — never `rz_raw` directly.

**Extraction cadence:** 1 season per slot, 4 slots/day (00:00 + 06:00 + 12:00 + 18:00) via launchd + `run_next_from_queue.sh`. Queue in `pipeline/cloud-run/schedules/sofascore_queue.txt`. Do not run back-to-back seasons manually — even 2 consecutive seasons triggers a 24-hour Cloudflare IP ban.

## Agent ecosystem

Four specialised agents live in `.claude/agents/`. Invoke the right one for the task:

| Agent | When to use | Cannot |
|---|---|---|
| **data-lead** | Vision, roadmap, priorities, governance, documentation | Write SQL, run pipelines, modify code |
| **data-engineer** | SQL, dbt models, BQ schemas, pipeline code, backfills | Update wiki, set strategy |
| **data-scout** | Player profiles, scouting reports, acquisition fit analysis | Match/team performance analysis |
| **match-analyst** | Zaragoza form, match breakdowns, player trends, league benchmarks | Transfer recommendations |

Each agent's `AGENT.md` defines its context-loading checklist, capabilities, hard limits, and output format. A new conversation using one of these agents must read its `AGENT.md` before doing anything else.

## General

- Don't invent statistics or dates. If you can't verify something, leave it as an open item.
- Keep `next-actions.md` forward-looking only — remove completed items and note them in `wiki/log.md` instead. `next-actions.md` has no Done sections; it only tracks pending and active work.
- **Never run `git push` (or anything else that touches the remote) without asking first, every time — a prior approval does not carry over to the next push.** Commit locally freely; pushing always needs an explicit go-ahead in that conversation.
