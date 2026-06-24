# Real Zaragoza

A long-running, open-ended analysis project on Real Zaragoza CF — on the pitch and off it.

## Why this exists

Real Zaragoza is a historic Spanish club (founded 1932, nine major titles including the 1995 Recopa de Europa) currently going through arguably its deepest crisis in nearly a century: relegated out of professional football into Primera RFEF in May 2026, playing away from a demolished home stadium, and mid-restructuring at boardroom level. That combination — rich history, active institutional turmoil, and a sporting project being rebuilt from the third tier up — makes it a good subject for sustained, structured tracking rather than a one-off writeup. This repo is meant to grow indefinitely: as seasons pass, players move, executives change, and the new stadium opens, the content here should be updated rather than replaced.

The project has two distinct halves:

1. **The institution** — ownership, boardroom, sporting direction, coaching staff, stadium, finances, history and identity.
2. **The football** — players, squads, results, statistics, both current and historical — eventually compared against other clubs.

## Structure

- **`wiki/`** — an LLM-maintained wiki, inspired by Andrej Karpathy's idea of a wiki that an LLM writes and maintains directly rather than humans editing prose by hand. Each page is small and atomic (one topic), dated, and sourced — facts get corrected and updated in place as they change, rather than left to rot next to newer information. Currently:
  - `history.md` — founding, honours, notable eras, relegations, stadium history.
  - `current-situation.md` — present-day ownership, board, coaching staff, sporting direction, and the ongoing stadium/institutional crisis.
  - More pages (players, season-by-season stats, comparative team data) will be added as the data-sourcing work below comes online.
- **`next-actions.md`** (repo root) — the backlog of planned work: data pulls, new wiki pages, open questions flagged inside the wiki itself. This is where ideas go before they're built — it is *not* part of the wiki.
- **`.claude/`** — instructions for Claude Code on how to work in this repo: wiki conventions, sourcing standards, and operating rules (see `.claude/CLAUDE.md`).

## Sources of truth

For anything about the club itself (history, ownership, staff, honours), [realzaragoza.com](https://www.realzaragoza.com/) and the [Spanish Wikipedia article](https://es.wikipedia.org/wiki/Real_Zaragoza) are treated as authoritative — where day-to-day press coverage disagrees with these two, these two win. Day-to-day news is still used to fill in things the wiki/official site don't cover (e.g. a coaching dismissal the week it happens), but anything time-sensitive is flagged as an open item until confirmed against the two primary sources.

For statistical data, the plan (tracked in `next-actions.md`) is to pull team data from **SofaScore** and player data from **Transfermarkt**.

## Where things stand

See `next-actions.md` for the live backlog. As of now: the institutional wiki pages (history + current situation) exist; data sourcing from SofaScore/Transfermarkt has not started yet.
