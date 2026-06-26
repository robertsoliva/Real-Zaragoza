"""
FotMob scraper — LaLiga2 (Segunda División) match and player stats.

Targets: leagueId=893055 (LaLiga2). Extend TARGET_LEAGUE_IDS for other leagues.
Collects: match results, per-player match stats, shot maps (xG matches only).

Run modes (env vars):
  Default               → 2024-25 full-season backfill
  SCRAPE_START/SCRAPE_END → explicit date range
  INCREMENTAL=true      → last 8 days (weekly scheduler mode)

FotMob coverage levels:
  xG      → full stats + xG/xA + shot coordinates
  ratings  → full stats, no xG/shots
  lower   → result only (1RFEF) — skipped for player stats
"""

import asyncio
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from playwright.async_api import async_playwright

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TARGET_LEAGUE_IDS = {893055}   # LaLiga2
REQUEST_DELAY_S   = 0.8
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
LOCAL_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "fotmob"


def resolve_date_range() -> tuple[date, date, str]:
    if os.environ.get("INCREMENTAL", "").lower() == "true":
        end = date.today()
        return end - timedelta(days=8), end, "incremental"
    raw_start = os.environ.get("SCRAPE_START")
    raw_end   = os.environ.get("SCRAPE_END")
    if raw_start and raw_end:
        return date.fromisoformat(raw_start), date.fromisoformat(raw_end), f"{raw_start}..{raw_end}"
    return date(2024, 8, 1), date(2025, 6, 30), "2024/2025 backfill"


def _to_int(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# FotMob API helpers
# ---------------------------------------------------------------------------

async def fetch_matches_for_date(page, d: date) -> list[dict]:
    date_str = d.strftime("%Y%m%d")
    data = await page.evaluate(f"""async () => {{
        const r = await fetch(
            'https://www.fotmob.com/api/data/matches?date={date_str}&timezone=Europe%2FMadrid'
        );
        if (!r.ok) return null;
        return await r.json();
    }}""")
    if not data or "leagues" not in data:
        return []
    out = []
    for league in data["leagues"]:
        if league.get("id") in TARGET_LEAGUE_IDS:
            for m in league.get("matches", []):
                out.append(m)
    return out


async def fetch_match_details(page, match_id) -> Optional[dict]:
    return await page.evaluate(f"""async () => {{
        const r = await fetch(
            'https://www.fotmob.com/api/data/matchDetails?matchId={match_id}'
        );
        if (!r.ok) return null;
        return await r.json();
    }}""")


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _sv(flat, key) -> Optional[float]:
    return (flat.get(key) or {}).get("stat", {}).get("value")


def _fv(flat, key, which):
    s = (flat.get(key) or {}).get("stat", {})
    return s.get("value") if which == "val" else s.get("total")


def parse_match_row(match_id: str, general: dict, coverage: str,
                    ingested_date: date, ingested_at: datetime) -> dict:
    home = general.get("homeTeam", {})
    away = general.get("awayTeam", {})
    match_date = (general.get("matchTimeUTCDate") or "")[:10] or None
    return {
        "match_id":         str(match_id),
        "match_date":       match_date,
        "match_round":      _to_int(general.get("matchRound")),
        "league_id":        str(general.get("leagueId", "")),
        "league_name":      general.get("leagueName"),
        "parent_league_id": str(general.get("parentLeagueId", "")),
        "match_time_utc":   general.get("matchTimeUTC"),
        "home_team_id":     str(home.get("id", "")),
        "home_team_name":   home.get("name"),
        "away_team_id":     str(away.get("id", "")),
        "away_team_name":   away.get("name"),
        "home_score":       None,
        "away_score":       None,
        "coverage_level":   coverage,
        "ingested_date":    ingested_date.isoformat(),
        "ingested_at":      ingested_at.isoformat(),
    }


def extract_scores(header: dict, match_row: dict) -> dict:
    teams = header.get("teams", [])
    if len(teams) >= 2:
        match_row["home_score"] = teams[0].get("score")
        match_row["away_score"] = teams[1].get("score")
    return match_row


def parse_player_stats(match_id: str, general: dict, ps_dict: dict,
                        ingested_date: date, ingested_at: datetime) -> list[dict]:
    match_date  = (general.get("matchTimeUTCDate") or "")[:10] or None
    match_round = _to_int(general.get("matchRound"))
    rows = []
    for pid, pdata in ps_dict.items():
        if not isinstance(pdata, dict) or not pdata.get("stats"):
            continue
        flat: dict = {}
        for group in pdata["stats"]:
            flat.update(group.get("stats", {}))

        def iv(key): return _sv(flat, key)
        def fv(key, w): return _fv(flat, key, w)

        rows.append({
            "match_id":                 str(match_id),
            "player_id":                str(pdata["id"]),
            "match_date":               match_date,
            "match_round":              match_round,
            "player_name":              pdata.get("name"),
            "team_id":                  str(pdata.get("teamId", "")),
            "team_name":                pdata.get("teamName"),
            "is_goalkeeper":            pdata.get("isGoalkeeper", False),
            "shirt_number":             pdata.get("shirtNumber"),
            "usual_position":           pdata.get("usualPosition"),
            "minutes_played":           iv("Minutes played"),
            "goals":                    iv("Goals"),
            "assists":                  iv("Assists"),
            "rating":                   iv("FotMob rating"),
            "expected_assists":         iv("Expected assists (xA)"),
            "xg_and_xa":                iv("xG + xA"),
            "accurate_passes":          fv("Accurate passes", "val"),
            "total_passes":             fv("Accurate passes", "tot"),
            "chances_created":          iv("Chances created"),
            "defensive_actions":        iv("Defensive actions"),
            "touches":                  iv("Touches"),
            "touches_opp_box":          iv("Touches in opposition box"),
            "passes_into_final_third":  iv("Passes into final third"),
            "long_balls_accurate":      fv("Accurate long balls", "val"),
            "long_balls_total":         fv("Accurate long balls", "tot"),
            "dispossessed":             iv("Dispossessed"),
            "tackles":                  iv("Tackles"),
            "blocks":                   iv("Blocks"),
            "clearances":               iv("Clearances"),
            "headed_clearances":        iv("Headed clearance"),
            "interceptions":            iv("Interceptions"),
            "recoveries":               iv("Recoveries"),
            "dribbled_past":            iv("Dribbled past"),
            "ground_duels_won":         fv("Ground duels won", "val"),
            "ground_duels_total":       fv("Ground duels won", "tot"),
            "aerial_duels_won":         fv("Aerial duels won", "val"),
            "aerial_duels_total":       fv("Aerial duels won", "tot"),
            "was_fouled":               iv("Was fouled"),
            "fouls_committed":          iv("Fouls committed"),
            "ingested_date":            ingested_date.isoformat(),
            "ingested_at":              ingested_at.isoformat(),
        })
    return rows


def parse_shots(match_id: str, general: dict, shots: list[dict],
                ingested_date: date, ingested_at: datetime) -> list[dict]:
    match_date  = (general.get("matchTimeUTCDate") or "")[:10] or None
    match_round = _to_int(general.get("matchRound"))
    rows = []
    for s in shots:
        ns = s.get("newScore") or [None, None]
        rows.append({
            "shot_id":                  str(s.get("id", "")),
            "match_id":                 str(match_id),
            "match_date":               match_date,
            "match_round":              match_round,
            "team_id":                  str(s.get("teamId", "")),
            "player_id":                str(s.get("playerId", "")),
            "player_name":              s.get("playerName"),
            "event_type":               s.get("eventType"),
            "shot_type":                s.get("shotType"),
            "situation":                s.get("situation"),
            "period":                   s.get("period"),
            "minute":                   s.get("min"),
            "minute_added":             s.get("minAdded"),
            "x":                        s.get("x"),
            "y":                        s.get("y"),
            "expected_goals":           s.get("expectedGoals"),
            "expected_goals_on_target": s.get("expectedGoalsOnTarget"),
            "is_on_target":             s.get("isOnTarget"),
            "is_blocked":               s.get("isBlocked"),
            "is_own_goal":              s.get("isOwnGoal"),
            "new_score_home":           ns[0] if len(ns) > 0 else None,
            "new_score_away":           ns[1] if len(ns) > 1 else None,
            "ingested_date":            ingested_date.isoformat(),
            "ingested_at":              ingested_at.isoformat(),
        })
    return rows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_to_bq(rows: list[dict], table: str, project_id: str):
    from google.cloud import bigquery
    if not rows:
        return
    client = bigquery.Client(project=project_id)
    full_table = f"{project_id}.rz_raw.{table}"
    errors = client.insert_rows_json(full_table, rows)
    if errors:
        print(f"  BQ errors ({table}): {errors[:2]}")
    else:
        print(f"  {len(rows):,} rows → {full_table}")


def save_local(payload: dict[str, list[dict]]):
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    for table, rows in payload.items():
        if not rows:
            continue
        path = LOCAL_DIR / f"{table}_{ts}.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        print(f"  {len(rows):,} rows → {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_scrape():
    project_id    = os.environ.get("GCP_PROJECT_ID")
    ingested_date = date.today()
    ingested_at   = datetime.now(timezone.utc)
    season_start, season_end, season_label = resolve_date_range()

    all_matches:      list[dict] = []
    all_player_stats: list[dict] = []
    all_shots:        list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page    = await browser.new_page(user_agent=UA)

        print("Warming up FotMob session...")
        await page.goto("https://www.fotmob.com", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # Phase 1 — enumerate match IDs
        print(f"\nPhase 1: collecting match IDs ({season_label})...")
        match_ids: dict[int, dict] = {}
        cur = season_start
        while cur <= season_end:
            matches = await fetch_matches_for_date(page, cur)
            for m in matches:
                if m["id"] not in match_ids:
                    match_ids[m["id"]] = m
            if matches:
                print(f"  {cur}: +{len(matches)} ({len(match_ids)} total)")
            cur += timedelta(days=1)
            await asyncio.sleep(REQUEST_DELAY_S)

        print(f"\n  Total: {len(match_ids)} matches")

        # Phase 2 — fetch detail for each
        print(f"\nPhase 2: fetching match details...")
        for i, (mid, _) in enumerate(match_ids.items(), 1):
            print(f"  [{i}/{len(match_ids)}] {mid}", end=" ")
            detail = await fetch_match_details(page, mid)
            if not detail:
                print("→ skip")
                await asyncio.sleep(REQUEST_DELAY_S)
                continue

            general   = detail.get("general", {})
            content   = detail.get("content", {})
            header    = detail.get("header", {})
            coverage  = general.get("coverageLevel", "lower")
            ps_dict   = content.get("playerStats") or {}
            shots_raw = (content.get("shotmap") or {}).get("shots") or []

            print(f"→ {coverage}, {len(ps_dict)} players, {len(shots_raw)} shots")

            mrow = parse_match_row(str(mid), general, coverage, ingested_date, ingested_at)
            mrow = extract_scores(header, mrow)
            all_matches.append(mrow)

            if ps_dict:
                all_player_stats.extend(
                    parse_player_stats(str(mid), general, ps_dict, ingested_date, ingested_at)
                )
            if shots_raw:
                all_shots.extend(
                    parse_shots(str(mid), general, shots_raw, ingested_date, ingested_at)
                )

            await asyncio.sleep(REQUEST_DELAY_S)

        await browser.close()

    print(f"\nSummary: {len(all_matches)} matches, {len(all_player_stats):,} player rows, {len(all_shots):,} shots")

    payload = {
        "fotmob_matches":            all_matches,
        "fotmob_player_match_stats": all_player_stats,
        "fotmob_shots":              all_shots,
    }
    if project_id:
        print(f"\nWriting to BigQuery ({project_id})...")
        for table, rows in payload.items():
            write_to_bq(rows, table, project_id)
    else:
        print("\nNo GCP_PROJECT_ID — saving locally...")
        save_local(payload)


if __name__ == "__main__":
    asyncio.run(run_scrape())
