# Next Actions

Running backlog of ideas/future work for this repo. Not a wiki page — this tracks what to *build*, the wiki tracks what we *know*. Move items to "Done" with a date when finished instead of deleting, so we keep a record of when things shipped.

## Data sourcing

- [ ] **SofaScore — team-level data.** Pull match results, fixtures, season stats (xG, possession, etc.) for Real Zaragoza and decide which other teams (rivals / divisional peers) are worth tracking for comparison.
- [ ] **Transfermarkt — player-level data.** Pull current squad: market values, contract expiry dates, transfer history, nationality/age/position. Decide refresh cadence (one-off snapshot vs. periodic re-pull).
- [ ] Decide on a storage format for scraped data (flat CSV/JSON in a `data/` folder vs. a small SQLite db) before the first real pull, so we don't have to migrate later.
- [ ] Define a scraping/refresh cadence (e.g. weekly during the season) and where that lives (manual run vs. scheduled job).

## Wiki content (Karpathy-style: atomic, sourced, append-only pages)

- [x] Reconcile `history.md` + `current-situation.md` against realzaragoza.com and Wikipedia as sources of truth (1932 founding/merger detail, stadium demolition, 1995 Recopa final score, Ibai Gómez as head coach) — 2026-06-24
- [x] Institution/football deep-dive pages: `wiki/finances.md` (debt history, 2026 capital increase, wage caps), `wiki/squad.md` (2026–27 rebuild), `wiki/identity-fan-culture.md` (nicknames, rivalries, ultras, anthem, socios), `wiki/records.md` (top scorer, appearances, Pichichi), `wiki/academy.md` (cantera structure, 2026 overhaul, graduates) — 2026-06-24
- [x] `wiki/README.md` index page — 2026-06-24
- [ ] Season-by-season results table (full history) — likely generated from the SofaScore pull once that exists, linked from `wiki/history.md`.
- [ ] Player pages — one atomic page per current first-team player once Transfermarkt data lands; should also replace `wiki/squad.md`'s prose roster with a structured table, and give `wiki/academy.md` a current (not 2018–19) graduate list.
- [ ] Standing task, not a one-off: periodically sweep every wiki page's "Open items" section for things that should now be resolvable — several are genuinely time-sensitive right now (new institutional president/general director names and Fernando López succession in `current-situation.md`; 2026–27 captaincy and the "at risk" players in `squad.md`; the Ander Herrera return and Francho/Azón contract renewals in `academy.md`).

## Infrastructure

- [x] Clone repo locally, scaffold `wiki/` + `next-actions.md` + `.claude/` — 2026-06-24
- [ ] Decide repo layout for data once sourcing starts: `data/sofascore/`, `data/transfermarkt/`, etc.
- [ ] Consider a lightweight script/notebook setup for the scraping work (language/tooling TBD).
