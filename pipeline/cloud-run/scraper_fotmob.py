"""
FotMob scraper — LaLiga2 (Segunda División) historical data.

Targets: leagueId=893055 (LaLiga2), season 2024-25 by default.
Collects: match results, per-player match stats, shot maps (xG matches only).

Phase 1: enumerate all match IDs by iterating daily matches endpoint.
Phase 2: fetch matchDetails for each match ID.
Phase 3: write to BQ (or local CSV if GCP_PROJECT_ID not set).

Coverage by FotMob level:
  xG      → full stats + shot map coordinates + xG, xA
  ratings  → full stats (no shot map coords, no xG)
  lower   → match result only (1RFEF, lower leagues)
"""

import asyncio
import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from playwright.async_api import async_playwright

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TARGET_LEAGUE_IDS = {893055}          # LaLiga2 in FotMob
SEASON_LABEL = "2024/2025"
SEASON_START = date(2024, 8, 1)
SEASON_END   = date(2025, 6, 30)
REQUEST_DELAY_S = 0.8                 # polite delay between API calls
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

LOCAL_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "fotmob"


# ---------------------------------------------------------------------------
# FotMob API helpers (all called inside page.evaluate to carry session cookies)
# ---------------------------------------------------------------------------

async def fetch_matches_for_date(page, d: date) -> list[dict]:
    """Return list of match dicts from /api/data/matches for one date."""
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
    matches = []
    for league in data["leagues"]:
        if league.get("id") in TARGET_LEAGUE_IDS:
            for m in league.get("matches", []):
                m["_leagueId"]   = league["id"]
                m["_leagueName"] = league.get("name", "")
                matches.append(m)
    return matches


async def fetch_match_details(page, match_id: int | str) -> Optional[dict]:
    """Return parsed matchDetails JSON or None on error."""
    data = await page.evaluate(f"""async () => {{
        const r = await fetch(
            'https://www.fotmob.com/api/data/matchDetails?matchId={match_id}'
        );
        if (!r.ok) return null;
        return await r.json();
    }}""")
    return data


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _stat_val(stat_obj: dict, key: str) -> Optional[float]:
    """Extract numeric value from playerStat group dict."""
    s = stat_obj.get(key, {}).get("stat", {})
    return s.get("value")


def _fraction_vals(stat_obj: dict, key: str) -> tuple[Optional[int], Optional[int]]:
    """Extract (value, total) for fractionWithPercentage stats."""
    s = stat_obj.get(key, {}).get("stat", {})
    return s.get("value"), s.get("total")


def parse_player_stats(match_id: str, general: dict, ps_dict: dict,
                        ingested_date: date, ingested_at: datetime) -> list[dict]:
    """Convert playerStats dict → list of flat rows for BQ."""
    rows = []
    for pid, pdata in ps_dict.items():
        if not isinstance(pdata, dict) or not pdata.get("stats"):
            continue
        # Flatten stat groups into one dict
        flat: dict = {}
        for group in pdata["stats"]:
            flat.update(group.get("stats", {}))

        def iv(key): return _stat_val(flat, key)
        def fv(key, sub): return _fraction_vals(flat, key)[0 if sub == "val" else 1]

        rows.append({
            "match_id":                 str(match_id),
            "player_id":                str(pdata["id"]),
            "ingested_date":            ingested_date.isoformat(),
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
            "ingested_at":              ingested_at.isoformat(),
        })
    return rows


def parse_shots(match_id: str, shots: list[dict],
                ingested_date: date, ingested_at: datetime) -> list[dict]:
    """Convert shot map array → list of flat rows for BQ."""
    rows = []
    for s in shots:
        new_score = s.get("newScore", [None, None])
        rows.append({
            "shot_id":                  str(s.get("id", "")),
            "match_id":                 str(match_id),
            "ingested_date":            ingested_date.isoformat(),
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
            "new_score_home":           new_score[0] if len(new_score) > 0 else None,
            "new_score_away":           new_score[1] if len(new_score) > 1 else None,
            "ingested_at":              ingested_at.isoformat(),
        })
    return rows


def parse_match_row(match_id: str, general: dict, coverage: str,
                    ingested_date: date, ingested_at: datetime) -> dict:
    home = general.get("homeTeam", {})
    away = general.get("awayTeam", {})
    header = {}  # scores come from header in full detail response
    return {
        "match_id":        str(match_id),
        "ingested_date":   ingested_date.isoformat(),
        "league_id":       str(general.get("leagueId", "")),
        "league_name":     general.get("leagueName"),
        "parent_league_id": str(general.get("parentLeagueId", "")),
        "match_time_utc":  general.get("matchTimeUTC"),
        "match_date":      general.get("matchTimeUTCDate", "")[:10] or None,
        "match_round":     general.get("matchRound"),
        "home_team_id":    str(home.get("id", "")),
        "home_team_name":  home.get("name"),
        "away_team_id":    str(away.get("id", "")),
        "away_team_name":  away.get("name"),
        "home_score":      None,
        "away_score":      None,
        "coverage_level":  coverage,
        "ingested_at":     ingested_at.isoformat(),
    }


def extract_scores(header: dict, match_row: dict) -> dict:
    """Fill home/away scores from header.teams."""
    teams = header.get("teams", [])
    if len(teams) >= 2:
        match_row["home_score"] = teams[0].get("score")
        match_row["away_score"] = teams[1].get("score")
    return match_row


# ---------------------------------------------------------------------------
# BigQuery writer
# ---------------------------------------------------------------------------

def write_to_bq(rows: list[dict], table: str, project_id: str):
    from google.cloud import bigquery
    if not rows:
        return
    client = bigquery.Client(project=project_id)
    full_table = f"{project_id}.rz_raw.{table}"
    errors = client.insert_rows_json(full_table, rows)
    if errors:
        print(f"  BQ errors for {table}: {errors[:3]}")
    else:
        print(f"  Wrote {len(rows)} rows → {full_table}")


# ---------------------------------------------------------------------------
# Local CSV writer
# ---------------------------------------------------------------------------

def save_local(data: dict[str, list[dict]]):
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    for table, rows in data.items():
        if not rows:
            continue
        path = LOCAL_DIR / f"{table}_{ts}.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        print(f"  Saved {len(rows)} rows → {path}")


# ---------------------------------------------------------------------------
# Main scrape loop
# ---------------------------------------------------------------------------

async def run_scrape():
    project_id = os.environ.get("GCP_PROJECT_ID")
    ingested_date = date.today()
    ingested_at   = datetime.now(timezone.utc)

    all_matches: list[dict] = []
    all_player_stats: list[dict] = []
    all_shots: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=UA)

        # Warm up: load fotmob so session cookies are set
        print("Warming up FotMob session...")
        await page.goto("https://www.fotmob.com", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # ---- Phase 1: enumerate all match IDs --------------------------------
        print(f"\nPhase 1: collecting match IDs for {SEASON_LABEL}...")
        match_ids: dict[int, dict] = {}  # match_id → basic match info
        cur = SEASON_START
        while cur <= SEASON_END:
            matches = await fetch_matches_for_date(page, cur)
            for m in matches:
                mid = m["id"]
                if mid not in match_ids:
                    match_ids[mid] = m
            if matches:
                print(f"  {cur}: +{len(matches)} matches ({len(match_ids)} total)")
            cur += timedelta(days=1)
            await asyncio.sleep(REQUEST_DELAY_S)

        print(f"\n  Total unique match IDs: {len(match_ids)}")

        # ---- Phase 2: fetch matchDetails for each ----------------------------
        print(f"\nPhase 2: fetching match details...")
        for i, (mid, minfo) in enumerate(match_ids.items(), 1):
            print(f"  [{i}/{len(match_ids)}] matchId={mid}", end=" ")
            detail = await fetch_match_details(page, mid)
            if not detail:
                print("→ no data")
                await asyncio.sleep(REQUEST_DELAY_S)
                continue

            general  = detail.get("general", {})
            content  = detail.get("content", {})
            header   = detail.get("header", {})
            coverage = general.get("coverageLevel", "lower")
            ps_dict  = content.get("playerStats") or {}
            shots_raw = (content.get("shotmap") or {}).get("shots") or []

            print(f"→ {coverage}, {len(ps_dict)} players, {len(shots_raw)} shots")

            # Match row
            mrow = parse_match_row(str(mid), general, coverage, ingested_date, ingested_at)
            mrow = extract_scores(header, mrow)
            all_matches.append(mrow)

            # Player stats (only for matches with real stats)
            if ps_dict:
                prows = parse_player_stats(str(mid), general, ps_dict, ingested_date, ingested_at)
                all_player_stats.extend(prows)

            # Shots (xG coverage only)
            if shots_raw:
                srows = parse_shots(str(mid), shots_raw, ingested_date, ingested_at)
                all_shots.extend(srows)

            await asyncio.sleep(REQUEST_DELAY_S)

        await browser.close()

    print(f"\nSummary:")
    print(f"  Matches:      {len(all_matches)}")
    print(f"  Player stats: {len(all_player_stats)}")
    print(f"  Shots:        {len(all_shots)}")

    # ---- Phase 3: write output -----------------------------------------------
    payload = {
        "fotmob_matches":           all_matches,
        "fotmob_player_match_stats": all_player_stats,
        "fotmob_shots":             all_shots,
    }

    if project_id:
        print(f"\nWriting to BigQuery project={project_id}...")
        for table, rows in payload.items():
            write_to_bq(rows, table, project_id)
    else:
        print("\nGCP_PROJECT_ID not set — saving locally...")
        save_local(payload)


if __name__ == "__main__":
    asyncio.run(run_scrape())
