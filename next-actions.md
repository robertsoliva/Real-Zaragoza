# Next Actions

Running backlog of ideas/future work for this repo. Not a wiki page — this tracks what to *build*, the wiki tracks what we *know*. Move items to "Done" with a date when finished instead of deleting, so we keep a record of when things shipped.

## Data sourcing

- [ ] **SofaScore — team-level data.** Pull match results, fixtures, season stats (xG, possession, etc.) for Real Zaragoza and decide which other teams (rivals / divisional peers) are worth tracking for comparison.
- [ ] **Transfermarkt — player-level data.** Pull current squad: market values, contract expiry dates, transfer history, nationality/age/position. Decide refresh cadence (one-off snapshot vs. periodic re-pull).
- [ ] Decide on a storage format for scraped data (flat CSV/JSON in a `data/` folder vs. a small SQLite db) before the first real pull, so we don't have to migrate later.
- [ ] Define a scraping/refresh cadence (e.g. weekly during the season) and where that lives (manual run vs. scheduled job).

## Wiki content (Karpathy-style: atomic, sourced, append-only pages)

- [ ] Season-by-season results table (full history) — likely generated from the SofaScore pull once that exists, linked from `wiki/history.md`.
- [ ] Player pages — one atomic page per current first-team player once Transfermarkt data lands.
- [ ] Institution deep-dive pages: ownership timeline (2022 takeover → 2026 capital increase, told as a timeline rather than a snapshot), stadium (La Romareda — capacity, redevelopment plans), academy/cantera output.
- [ ] Confirm and fill in the two open items flagged in `wiki/current-situation.md` (new institutional president / general director names; David Navarro's status for 2026–27) once public.
- [ ] Confirm the open item flagged in `wiki/history.md` (1932 founding/merger details against the club's official history page).

## Infrastructure

- [x] Clone repo locally, scaffold `wiki/` + `next-actions.md` + `.claude/` — 2026-06-24
- [ ] Decide repo layout for data once sourcing starts: `data/sofascore/`, `data/transfermarkt/`, etc.
- [ ] Consider a lightweight script/notebook setup for the scraping work (language/tooling TBD).
