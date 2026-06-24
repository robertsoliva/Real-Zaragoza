# Real-Zaragoza repo — instructions for Claude

## README.md is frozen

As of 2026-06-24, the user has explicitly locked `README.md` — **do not edit it**, for any reason, even as a side effect of other work (new wiki pages, restructuring, etc.), unless the user explicitly asks to lift this freeze in that conversation. It's intentionally short; don't "helpfully" expand it back out.

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

## Data sourcing (future)

When SofaScore/Transfermarkt data pulls start (tracked in `next-actions.md`), raw data belongs in a `data/` directory, separate from `wiki/`. Wiki pages can reference/summarize that data but shouldn't be the dumping ground for raw scraped tables.

## General

- Don't invent statistics or dates. If you can't verify something, leave it as an open item.
- Keep `next-actions.md` up to date as work gets done — move finished items to done with a date instead of deleting them.
- **Never run `git push` (or anything else that touches the remote) without asking first, every time — a prior approval does not carry over to the next push.** Commit locally freely; pushing always needs an explicit go-ahead in that conversation.
