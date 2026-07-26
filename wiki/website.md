> **Status:** Living document. Last updated 2026-07-26.

# Website — RZ Analytics

Local Flask analytics app for the Real Zaragoza data platform. Internal scouting and stats tool; not yet publicly deployed.

---

## TL;DR

- Flask app at `website/`, launched via `bash website/start.sh`
- Requires `ANTHROPIC_API_KEY` (Claude API) and GCP Application Default Credentials
- Four pages: Home, Squad, Match Calculator, Scouting (added 2026-07-26)
- Scouting page is the core feature: player selector → full TM profile + stats + financial fit + Claude verdict

---

## Model

**Type:** Web application  
**Relationships:**
- [architecture.md](./architecture.md) — underlying data platform (BigQuery, dbt layers)
- [wage-model.md](./wage-model.md) — BQML wage predictions surfaced in scouting reports
- [finances.md](./finances.md) — 1RFEF budget context used for financial fit assessment

---

## Tech stack

| Layer | Choice |
|---|---|
| Server | Python Flask (debug mode, port 5050) |
| Data | `google-cloud-bigquery` — queries `gold.agg_scouting_player_season`, `gold.agg_league_player_benchmarks`, `gold.fct_player_season_stats`, `silver.rz_squad` |
| AI | `anthropic` Python SDK — `claude-sonnet-4-6`, called per report request |
| Frontend | Vanilla HTML/CSS/JS, no framework. Dark theme (Real Zaragoza colours). |

---

## Pages

### `/` — Home
Feature overview cards, links to all pages.

### `/squad` — Squad
Transfermarkt squad cards for Real Zaragoza with hover overlay. Data from `silver.rz_squad` — populated by the quarterly TM local run (next: Oct 1 2026). Currently empty between runs.

### `/calculator` — Match Calculator
Legacy fit-score tool (predates the scouting page). Loads players from `gold.fct_player_season_stats` (latest season per league, ≥450 min, 1RFEF excluded). Computes a 0-10 fit score (position_need + output_quality + league_adjustment + experience) and generates a 3-sentence Claude verdict.

### `/scouting` — Scouting *(added 2026-07-26)*
The primary scouting tool. Loads **6,002 players** from `gold.agg_scouting_player_season` (all leagues, latest season, ≥450 min). Report includes:

**Player selector:** Search by name, filter by league + position (G/D/M/F).

**Report sections:**
1. **Player header** — name, TM position, club, league, total minutes, avg rating badge
2. **Profile cards** — nationality, DOB + age, height · foot, previous club (all from TM)
3. **Market row** — TM market value, contract expiry (with months-remaining note), estimated wage (weekly + annual) with source badge (`capology_actual` = confirmed / `bqml_estimate` = model)
4. **Financial fit** — green/amber/red indicator with three sub-components: wage tier (vs 1RFEF budget ~€5–6M), transfer route (free/loan/buy based on market value and contract length), age profile (youth/young/prime/experienced/veteran)
5. **Stats grid** — 12 stats in 3 groups (Attacking / Passing / Defensive) with gold benchmark bars showing performance relative to league-position average (from `gold.agg_league_player_benchmarks`)
6. **Scout Verdict** — 5-sentence Claude narrative covering player type, statistical assessment, Zaragoza fit, financial picture, final recommendation (Sign / Loan / Monitor / Pass)

**Financial fit logic (1RFEF context):**
- Wage tiers: <€100k (very affordable) / €100–250k (affordable) / €250–500k (costly) / >€500k (out of budget)
- Transfer routes: free agent / expiring contract / <€300k buy / €300k–1M loan-or-buy / €1–3M loan preferred / >€3M large fee
- Overall green: affordable wage + feasible transfer; red: out-of-budget or large-fee-required

---

## Data quality notes

- **TM coverage:** ~5,032 of 20,301 players in `agg_scouting_player_season` have TM data (market value, age, height, nationality). The rest have SofaScore stats only, with BQML wage estimate if available.
- **Wage coverage:** 163 `capology_actual` (top-5 EU confirmed wages) + 11,726 `bqml_estimate` + ~8,400 NULL (no TM market value to anchor the model).
- **Height/foot:** fixed 2026-07-26 — some TM competition pages use a 9-column layout that shifts columns; height/foot swap corrected in `silver_tm_players.sql` via REGEXP. Contract expiry and foot preference remain NULL for many leagues (LaLiga2, Serie B, etc.) pending scraper fix in Oct 2026.
- **Name matching:** TM join on normalized player_name + team_name — ~30% miss rate due to diacritics and name transliteration differences.

---

## Running locally

```bash
# Set API key once in ~/.zshrc:
export ANTHROPIC_API_KEY='sk-ant-...'

# Launch:
bash website/start.sh
# → http://127.0.0.1:5050
```

GCP ADC must be configured (`gcloud auth application-default login`).

---

## Pending

- **Squad page** — will populate automatically after Oct 1 TM quarterly run
- **Match results page** — from `gold.fct_rz_matches`
- **Player detail pages** — per-player stat breakdown from `gold.fct_player_season_stats`
- **League comparison views** — Zaragoza vs. LaLiga2 averages from `gold.agg_league_player_benchmarks`
- **Public deployment** — after backfills complete (~2026-07-30) and squad page is current

---

## Sources

- [Real Zaragoza analytics platform — architecture.md](./architecture.md)
