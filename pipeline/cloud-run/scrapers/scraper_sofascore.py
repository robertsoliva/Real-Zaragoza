"""
SofaScore scraper — multi-league match, player, shot, and team stats.

SofaScore tournament IDs:
  LaLiga2            = 54       Serie B (Italy)      = 53
  1RFEF              = 17073    Ligue 2 (France)     = 182
  Romanian SuperLiga = 152      J1 League (Japan)    = 196
  FIFA World Cup     = 16       Turkish Süper Lig    = 52
  Norwegian Elitser. = 20       Austrian Bundesliga  = 45
  Korean K League 1  = 410      Eredivisie (NL 1st)  = 37
  Belgian Pro League = 38       Liga Portugal        = 238
  Bundesliga         = 35       2. Bundesliga        = 44
  Premier League     = 17       La Liga              = 8
  Serie A            = 23       Ligue 1              = 34
  Real Zaragoza team_id = 2815

Known season IDs (run seasons_lookup.py to discover others):
  LaLiga2 2024-25 = 62048    LaLiga2 2025-26 = 77558
  1RFEF   2024-25 = 64430    1RFEF   2025-26 = 77727

Env vars:
  TOURNAMENT_ID  — SofaScore tournament/league ID (required; default 54 = LaLiga2)
  SEASON_ID      — SofaScore season ID (required; default 62048 = 2024-25)
  INCREMENTAL    — "true" → only matches in last 14 days
  ROUND_START    — resume a backfill from this round number (default 1)
  GCP_PROJECT_ID — write to BigQuery when set; otherwise save local CSV
  BQ_DATASET     — BQ dataset to write to (default: raw; use wc_2026 for World Cup)

BQ tables (configurable via BQ_DATASET, default raw):
  sofascore_matches, sofascore_player_match_stats,
  sofascore_shots, sofascore_team_match_stats
"""

import asyncio
import logging
import os
import random
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sofascore")

BASE_URL = "https://api.sofascore.com"

LEAGUE_NAMES: dict[str, str] = {
    "54":    "LaLiga2",
    "17073": "1RFEF",
    "53":    "Serie B",
    "182":   "Ligue 2",
    "152":   "Romanian SuperLiga",
    "196":   "J1 League",
    "16":    "FIFA World Cup",
    "52":    "Turkish Süper Lig",
    "20":    "Norwegian Eliteserien",
    "45":    "Austrian Bundesliga",
    "410":   "Korean K League 1",
    "390":   "Brasileirao Serie B",
    "210":   "Mozzart Bet Superliga",
    "242":   "MLS",
    "40":    "Allsvenskan",
    "131":   "Eerste Divisie",
    "685":   "Moldovan Super Liga",
    "37":    "Eredivisie",
    "38":    "Belgian Pro League",
    "238":   "Liga Portugal",
    "35":    "Bundesliga",
    "44":    "2. Bundesliga",
    "17":    "Premier League",
    "8":     "La Liga",
    "23":    "Serie A",
    "34":    "Ligue 1",
}

# Stat fields used to detect whether SofaScore returned real player stats.
# If none of these are populated for any player in a match, we skip the BQ
# write (stats not yet processed or league has no detailed coverage).
_PLAYER_STAT_PROBE = ("minutes_played", "total_passes", "touches", "rating")

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://www.sofascore.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}
LOCAL_DIR = Path(__file__).parents[3] / "data" / "raw" / "sofascore"
REQUEST_DELAY    = 5.0   # seconds between match-level API calls (3 endpoints per match)
ROUND_DELAY      = 20.0  # seconds between rounds (longer pause to avoid IP blocks)
INCREMENTAL_DAYS = 14
MAX_CUP_EVENTS   = 50    # safety cap: cuptrees for league seasons can return thousands of IDs


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

class NetworkClient:
    def __init__(self):
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self):
        self._session = AsyncSession(impersonate="chrome124")
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def get(self, endpoint: str, retries: int = 3) -> Optional[dict]:
        url = f"{BASE_URL}{endpoint}"
        for attempt in range(retries):
            try:
                resp = await asyncio.wait_for(
                    self._session.get(url, headers=HEADERS, timeout=30),
                    timeout=60,
                )
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code in (429, 503):
                    wait = 5 * (2 ** attempt) + random.uniform(0, 3)
                    log.warning(f"Rate limit {resp.status_code} — sleeping {wait:.1f}s")
                    await asyncio.sleep(wait)
                    continue
                log.debug(f"{endpoint} → {resp.status_code}")
                return None
            except asyncio.TimeoutError:
                log.warning(f"Hard timeout (60s) on {endpoint} — attempt {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                log.error(f"Request failed for {endpoint}: {e}")
                return None
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _int(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def _float(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def _frac(s) -> tuple[Optional[int], Optional[int]]:
    """'23/45 (51%)' → (23, 45).  '394' → (394, None)."""
    if s is None:
        return None, None
    m = re.match(r"(\d+)/(\d+)", str(s))
    if m:
        return int(m.group(1)), int(m.group(2))
    try:
        return int(s), None
    except (ValueError, TypeError):
        return None, None


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_match_row(event: dict, tournament_id: str, season_id: str,
                    league_name: str,
                    ingested_date: date, ingested_at: datetime) -> dict:
    home = event.get("homeTeam") or {}
    away = event.get("awayTeam") or {}
    ts   = event.get("startTimestamp")
    match_date_str = (
        datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") if ts else None
    )
    return {
        "match_id":       str(event["id"]),
        "match_date":     match_date_str,
        "match_round":    _int((event.get("roundInfo") or {}).get("round")),
        "tournament_id":  tournament_id,
        "season_id":      season_id,
        "league_name":    league_name,
        "home_team_id":   str(home.get("id", "")),
        "home_team_name": home.get("name"),
        "away_team_id":   str(away.get("id", "")),
        "away_team_name": away.get("name"),
        "home_score":     _int((event.get("homeScore") or {}).get("current")),
        "away_score":     _int((event.get("awayScore") or {}).get("current")),
        "status":         (event.get("status") or {}).get("type"),
        "ingested_date":  ingested_date.isoformat(),
        "ingested_at":    ingested_at.isoformat(),
    }


def _player_rows_have_stats(rows: list[dict]) -> bool:
    """Return True if at least one row has at least one real stat populated."""
    return any(row.get(f) is not None for row in rows for f in _PLAYER_STAT_PROBE)


def parse_player_stats(match_id: str, match_date: Optional[str], match_round: Optional[int],
                       lineup_data: dict,
                       tournament_id: str, season_id: str, league_name: str,
                       ingested_date: date, ingested_at: datetime) -> list[dict]:
    rows = []
    _logged_empty_stats = False
    for side in ("home", "away"):
        is_home   = side == "home"
        side_data = lineup_data.get(side) or {}
        team      = side_data.get("team") or {}
        team_id   = str(team.get("id", ""))
        team_name = team.get("name")

        all_players = side_data.get("players", []) + side_data.get("substitutes", [])
        for p in all_players:
            player    = p.get("player") or {}
            stats_raw = p.get("statistics")

            # Log once per match when stats are missing so we can diagnose the root cause
            if not _logged_empty_stats and not stats_raw:
                stat_keys = list(stats_raw.keys()) if isinstance(stats_raw, dict) else None
                log.debug(
                    f"  [{match_id}] {side} first player stats_raw={repr(stats_raw)!r} "
                    f"keys={stat_keys} — may be null for {league_name}"
                )
                _logged_empty_stats = True

            stats = stats_raw if isinstance(stats_raw, dict) else {}

            rows.append({
                "match_id":            match_id,
                "player_id":           str(player.get("id", "")),
                "match_date":          match_date,
                "match_round":         match_round,
                "tournament_id":       tournament_id,
                "season_id":           season_id,
                "league_name":         league_name,
                "player_name":         player.get("name"),
                "team_id":             team_id,
                "team_name":           team_name,
                "is_home":             is_home,
                "position":            p.get("position"),
                "shirt_number":        _int(p.get("shirtNumber")),
                "is_substitute":       bool(p.get("substitute", False)),
                "captain":             bool(p.get("captain", False)),
                "minutes_played":      _int(stats.get("minutesPlayed")),
                "goals":               _int(stats.get("goals")),
                "goal_assists":        _int(stats.get("goalAssist")),
                "rating":              _float(stats.get("rating")),
                "total_passes":        _int(stats.get("totalPass")),
                "accurate_passes":     _int(stats.get("accuratePass")),
                "total_long_balls":    _int(stats.get("totalLongBalls")),
                "accurate_long_balls": _int(stats.get("accurateLongBalls")),
                "total_crosses":       _int(stats.get("totalCross")),
                "accurate_crosses":    _int(stats.get("accurateCross")),
                "key_passes":          _int(stats.get("keyPass")),
                "total_shots":         _int(stats.get("totalShots")),
                "shots_on_target":     _int(stats.get("onTargetScoringAttempt")),
                "aerial_won":          _int(stats.get("aerialWon")),
                "aerial_lost":         _int(stats.get("aerialLost")),
                "duel_won":            _int(stats.get("duelWon")),
                "duel_lost":           _int(stats.get("duelLost")),
                "challenge_lost":      _int(stats.get("challengeLost")),
                "total_tackle":        _int(stats.get("totalTackle")),
                "won_tackle":          _int(stats.get("wonTackle")),
                "interceptions":       _int(stats.get("interceptionWon")),
                "total_clearance":     _int(stats.get("totalClearance")),
                "ball_recovery":       _int(stats.get("ballRecovery")),
                "dispossessed":        _int(stats.get("dispossessed")),
                "was_fouled":          _int(stats.get("wasFouled")),
                "fouls":               _int(stats.get("fouls")),
                "touches":             _int(stats.get("touches")),
                "possession_lost":     _int(stats.get("possessionLostCtrl")),
                "unsuccessful_touch":  _int(stats.get("unsuccessfulTouch")),
                "yellow_cards":        _int(stats.get("yellowCards")),
                "red_cards":           _int(stats.get("redCards")),
                "saves":               _int(stats.get("saves")),
                "expected_goals":      _float(stats.get("expectedGoals")),
                "expected_assists":    _float(stats.get("expectedAssists")),
                "ingested_date":       ingested_date.isoformat(),
                "ingested_at":         ingested_at.isoformat(),
            })
    return rows


def parse_team_stats(match_id: str, match_date: Optional[str], match_round: Optional[int],
                     home_team_id: str, home_team_name: Optional[str],
                     away_team_id: str, away_team_name: Optional[str],
                     stats_data: dict,
                     tournament_id: str, season_id: str, league_name: str,
                     ingested_date: date, ingested_at: datetime) -> list[dict]:
    periods    = stats_data.get("statistics") or []
    all_period = next((p for p in periods if p.get("period") == "ALL"), periods[0] if periods else None)
    if not all_period:
        return []

    flat_val: dict[str, tuple] = {}
    flat_str: dict[str, tuple] = {}
    for group in all_period.get("groups") or []:
        for item in group.get("statisticsItems") or []:
            key = item.get("key")
            if key and key not in flat_val:
                flat_val[key] = (item.get("homeValue"), item.get("awayValue"))
                flat_str[key] = (item.get("home"), item.get("away"))

    def iv(key, idx) -> Optional[int]:
        vals = flat_val.get(key, (None, None))
        return _int(vals[idx] if idx < len(vals) else None)

    def fv(key, idx) -> tuple[Optional[int], Optional[int]]:
        strs = flat_str.get(key, (None, None))
        return _frac(strs[idx] if idx < len(strs) else None)

    rows = []
    for idx, (side, team_id, team_name) in enumerate([
        ("home", home_team_id, home_team_name),
        ("away", away_team_id, away_team_name),
    ]):
        lb_acc, lb_tot = fv("accurateLongBalls", idx)
        cr_acc, cr_tot = fv("accurateCross", idx)
        gd_won, gd_tot = fv("groundDuelsPercentage", idx)
        ad_won, ad_tot = fv("aerialDuelsPercentage", idx)
        dr_won, dr_tot = fv("dribblesPercentage", idx)
        ft_acc, ft_tot = fv("finalThirdPhaseStatistic", idx)

        rows.append({
            "match_id":              match_id,
            "match_date":            match_date,
            "match_round":           match_round,
            "tournament_id":         tournament_id,
            "season_id":             season_id,
            "league_name":           league_name,
            "team_id":               team_id,
            "team_name":             team_name,
            "side":                  side,
            "possession_pct":        iv("ballPossession", idx),
            "total_shots":           iv("totalShotsOnGoal", idx),
            "shots_on_target":       iv("shotsOnGoal", idx),
            "shots_off_target":      iv("shotsOffGoal", idx),
            "blocked_shots":         iv("blockedScoringAttempt", idx),
            "shots_on_woodwork":     iv("hitWoodwork", idx),
            "shots_inside_box":      iv("totalShotsInsideBox", idx),
            "shots_outside_box":     iv("totalShotsOutsideBox", idx),
            "big_chances":           iv("bigChanceCreated", idx),
            "big_chances_scored":    iv("bigChanceScored", idx),
            "big_chances_missed":    iv("bigChanceMissed", idx),
            "corners":               iv("cornerKicks", idx),
            "offsides":              iv("offsides", idx),
            "fouls":                 iv("fouls", idx),
            "yellow_cards":          iv("yellowCards", idx),
            "red_cards":             iv("redCards", idx),
            "total_passes":          iv("passes", idx),
            "accurate_passes":       iv("accuratePasses", idx),
            "accurate_long_balls":   lb_acc,
            "total_long_balls":      lb_tot,
            "accurate_crosses":      cr_acc,
            "total_crosses":         cr_tot,
            "touches_in_opp_box":    iv("touchesInOppBox", idx),
            "final_third_entries":   iv("finalThirdEntries", idx),
            "final_third_acc":       ft_acc,
            "final_third_total":     ft_tot,
            "total_tackles":         iv("totalTackle", idx),
            "won_tackles":           iv("wonTacklePercent", idx),
            "interceptions":         iv("interceptionWon", idx),
            "clearances":            iv("totalClearance", idx),
            "ball_recoveries":       iv("ballRecovery", idx),
            "errors_leading_to_shot":iv("errorsLeadToShot", idx),
            "goalkeeper_saves":      iv("goalkeeperSaves", idx),
            "ground_duels_won":      gd_won,
            "total_ground_duels":    gd_tot,
            "aerial_duels_won":      ad_won,
            "total_aerial_duels":    ad_tot,
            "dribbles_completed":    dr_won,
            "total_dribbles":        dr_tot,
            "dispossessed":          iv("dispossessed", idx),
            "ingested_date":         ingested_date.isoformat(),
            "ingested_at":           ingested_at.isoformat(),
        })
    return rows


def parse_shots(match_id: str, match_date: Optional[str], match_round: Optional[int],
                shotmap: list[dict],
                tournament_id: str, season_id: str, league_name: str,
                ingested_date: date, ingested_at: datetime) -> list[dict]:
    rows = []
    for shot in shotmap:
        player = shot.get("player") or {}
        pc     = shot.get("playerCoordinates") or {}
        gm     = shot.get("goalMouthCoordinates") or {}
        bk     = shot.get("blockCoordinates") or {}
        rows.append({
            "shot_id":             str(shot.get("id", "")),
            "match_id":            match_id,
            "match_date":          match_date,
            "match_round":         match_round,
            "tournament_id":       tournament_id,
            "season_id":           season_id,
            "league_name":         league_name,
            "player_id":           str(player.get("id", "")),
            "player_name":         player.get("name"),
            "is_home":             bool(shot.get("isHome", False)),
            "minute":              _int(shot.get("time")),
            "added_time":          _int(shot.get("addedTime")),
            "time_seconds":        _int(shot.get("timeSeconds")),
            "x":                   _float(pc.get("x")),
            "y":                   _float(pc.get("y")),
            "goal_mouth_x":        _float(gm.get("x")),
            "goal_mouth_y":        _float(gm.get("y")),
            "goal_mouth_z":        _float(gm.get("z")),
            "goal_mouth_location": shot.get("goalMouthLocation"),
            "block_x":             _float(bk.get("x")),
            "block_y":             _float(bk.get("y")),
            "body_part":           shot.get("bodyPart"),
            "shot_type":           shot.get("shotType"),
            "situation":           shot.get("situation"),
            "xg":                  _float(shot.get("xg")),
            "ingested_date":       ingested_date.isoformat(),
            "ingested_at":         ingested_at.isoformat(),
        })
    return rows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_to_bq(rows: list[dict], table: str, project_id: str, dataset: str = "raw") -> None:
    from google.cloud import bigquery
    if not rows:
        return
    try:
        client     = bigquery.Client(project=project_id)
        full_table = f"{project_id}.{dataset}.{table}"
        errors     = client.insert_rows_json(full_table, rows)
        if errors:
            log.error(f"BQ errors ({table}): {errors[:2]}")
        else:
            log.info(f"  {len(rows):,} rows → {full_table}")
    except Exception as e:
        log.error(f"BQ write failed ({table}), skipping batch: {e}")


def save_local(payload: dict[str, list[dict]]) -> None:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    for table, rows in payload.items():
        if not rows:
            continue
        path = LOCAL_DIR / f"{table}_{ts}.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        log.info(f"  {len(rows):,} rows → {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def _scrape_event(
    client: "NetworkClient",
    event: dict,
    tournament_id: str,
    season_id: str,
    league_name: str,
    ingested_date: date,
    ingested_at: datetime,
    r_matches: list,
    r_players: list,
    r_shots: list,
    r_teams: list,
) -> int:
    """Scrape one finished event and append rows into the provided lists. Returns skipped player count."""
    mid       = str(event["id"])
    match_row = parse_match_row(event, tournament_id, season_id, league_name,
                                ingested_date, ingested_at)
    match_date  = match_row["match_date"]
    match_round = match_row["match_round"]
    home_id, home_name = match_row["home_team_id"], match_row["home_team_name"]
    away_id, away_name = match_row["away_team_id"], match_row["away_team_name"]

    log.info(f"  [{mid}] {home_name} vs {away_name} ({match_date})")
    r_matches.append(match_row)
    skipped = 0

    lineup_data = await client.get(f"/api/v1/event/{mid}/lineups")
    if lineup_data:
        player_rows = parse_player_stats(
            mid, match_date, match_round, lineup_data,
            tournament_id, season_id, league_name,
            ingested_date, ingested_at,
        )
        if player_rows and _player_rows_have_stats(player_rows):
            r_players.extend(player_rows)
            log.info(f"    {len(player_rows)} player rows")
        elif player_rows:
            skipped += len(player_rows)
            log.warning(
                f"    [{mid}] player stats all-null ({len(player_rows)} rows skipped) — "
                f"SofaScore may not have processed this match yet or "
                f"{league_name} lacks detailed coverage"
            )
    await asyncio.sleep(random.uniform(REQUEST_DELAY * 0.8, REQUEST_DELAY * 1.2))

    stats_data = await client.get(f"/api/v1/event/{mid}/statistics")
    if stats_data:
        r_teams.extend(parse_team_stats(
            mid, match_date, match_round,
            home_id, home_name, away_id, away_name,
            stats_data, tournament_id, season_id, league_name,
            ingested_date, ingested_at,
        ))
    await asyncio.sleep(random.uniform(REQUEST_DELAY * 0.8, REQUEST_DELAY * 1.2))

    shot_data = await client.get(f"/api/v1/event/{mid}/shotmap")
    if shot_data:
        rows = parse_shots(
            mid, match_date, match_round,
            shot_data.get("shotmap") or [],
            tournament_id, season_id, league_name,
            ingested_date, ingested_at,
        )
        r_shots.extend(rows)
        log.info(f"    {len(rows)} shots")
    await asyncio.sleep(random.uniform(REQUEST_DELAY * 0.8, REQUEST_DELAY * 1.2))
    return skipped


async def run_scrape() -> None:
    project_id    = os.environ.get("GCP_PROJECT_ID")
    bq_dataset    = os.environ.get("BQ_DATASET", "raw")
    tournament_id = os.environ.get("TOURNAMENT_ID", "54")    # default LaLiga2
    season_id     = os.environ.get("SEASON_ID", "62048")     # default 2024-25
    incremental   = os.environ.get("INCREMENTAL", "").lower() == "true"
    round_start   = int(os.environ.get("ROUND_START", "1"))
    ingested_date = date.today()
    ingested_at   = datetime.now(timezone.utc)
    league_name   = LEAGUE_NAMES.get(tournament_id, f"tournament_{tournament_id}")

    cutoff_ts: Optional[int] = None
    if incremental:
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=INCREMENTAL_DAYS)
        cutoff_ts = int(cutoff_dt.timestamp())
        log.info(f"Incremental mode: matches since {cutoff_dt.date()}")
    else:
        log.info(f"Full season mode: tournament={tournament_id} ({league_name}), season={season_id}")

    total_matches = total_players = total_shots = total_team = total_skipped_players = 0

    async with NetworkClient() as client:
        # 1. Get available rounds for the season
        rounds_data = await client.get(
            f"/api/v1/unique-tournament/{tournament_id}/season/{season_id}/rounds"
        )
        if not rounds_data:
            log.error("Could not fetch rounds — check TOURNAMENT_ID and SEASON_ID")
            return
        rounds = [r["round"] for r in (rounds_data.get("rounds") or [])]
        log.info(f"Found {len(rounds)} rounds in tournament={tournament_id} season={season_id}")
        if round_start > 1:
            log.info(f"Resuming from round {round_start}")

        for round_num in rounds:
            if round_num < round_start:
                continue
            # 2. Matches in this round
            events_data = await client.get(
                f"/api/v1/unique-tournament/{tournament_id}/season/{season_id}"
                f"/events/round/{round_num}"
            )
            if not events_data:
                await asyncio.sleep(ROUND_DELAY)
                continue

            events   = events_data.get("events") or []
            finished = [
                e for e in events
                if (e.get("status") or {}).get("type") == "finished"
                and (cutoff_ts is None or (e.get("startTimestamp") or 0) >= cutoff_ts)
            ]
            if not finished:
                await asyncio.sleep(ROUND_DELAY)
                continue

            log.info(f"Round {round_num}: {len(finished)} finished matches")
            await asyncio.sleep(random.uniform(ROUND_DELAY * 0.8, ROUND_DELAY * 1.2))

            r_matches: list[dict] = []
            r_players: list[dict] = []
            r_shots:   list[dict] = []
            r_teams:   list[dict] = []

            for event in finished:
                skipped = await _scrape_event(
                    client, event, tournament_id, season_id, league_name,
                    ingested_date, ingested_at,
                    r_matches, r_players, r_shots, r_teams,
                )
                total_skipped_players += skipped

            # Flush this round immediately — transient BQ errors only lose one round
            if project_id:
                write_to_bq(r_matches, "sofascore_matches",            project_id, bq_dataset)
                write_to_bq(r_players, "sofascore_player_match_stats", project_id, bq_dataset)
                write_to_bq(r_teams,   "sofascore_team_match_stats",   project_id, bq_dataset)
                write_to_bq(r_shots,   "sofascore_shots",              project_id, bq_dataset)
            else:
                save_local({
                    "sofascore_matches":            r_matches,
                    "sofascore_player_match_stats": r_players,
                    "sofascore_shots":              r_shots,
                    "sofascore_team_match_stats":   r_teams,
                })
            total_matches += len(r_matches)
            total_players += len(r_players)
            total_shots   += len(r_shots)
            total_team    += len(r_teams)

        # 6. Cup/playoff rounds — only available via cuptrees, not the rounds endpoint
        #    (e.g. WC knockout stage: R32, R16, QF, SF, Final)
        cup_data = await client.get(
            f"/api/v1/unique-tournament/{tournament_id}/season/{season_id}/cuptrees"
        )
        if cup_data:
            cup_event_ids: list[int] = []
            for tree in cup_data.get("cupTrees") or []:
                for rnd in tree.get("rounds") or []:
                    for block in rnd.get("blocks") or []:
                        cup_event_ids.extend(block.get("events") or [])

            if cup_event_ids:
                log.info(f"Cup bracket: {len(cup_event_ids)} events found")
                if len(cup_event_ids) > MAX_CUP_EVENTS:
                    log.warning(
                        f"Cup bracket has {len(cup_event_ids)} events (>{MAX_CUP_EVENTS}) — "
                        f"looks like a full-season tree, not a real playoff. Skipping."
                    )
                    cup_event_ids = []

                cup_matches: list[dict] = []
                cup_players: list[dict] = []
                cup_shots:   list[dict] = []
                cup_teams:   list[dict] = []

                for eid in cup_event_ids:
                    await asyncio.sleep(random.uniform(REQUEST_DELAY * 0.8, REQUEST_DELAY * 1.2))
                    event_data = await client.get(f"/api/v1/event/{eid}")
                    event = (event_data or {}).get("event") or {}
                    if not event:
                        continue
                    if (event.get("status") or {}).get("type") != "finished":
                        continue
                    if cutoff_ts and (event.get("startTimestamp") or 0) < cutoff_ts:
                        continue
                    await asyncio.sleep(random.uniform(ROUND_DELAY * 0.8, ROUND_DELAY * 1.2))
                    skipped = await _scrape_event(
                        client, event, tournament_id, season_id, league_name,
                        ingested_date, ingested_at,
                        cup_matches, cup_players, cup_shots, cup_teams,
                    )
                    total_skipped_players += skipped

                if cup_matches:
                    if project_id:
                        write_to_bq(cup_matches, "sofascore_matches",            project_id, bq_dataset)
                        write_to_bq(cup_players, "sofascore_player_match_stats", project_id, bq_dataset)
                        write_to_bq(cup_teams,   "sofascore_team_match_stats",   project_id, bq_dataset)
                        write_to_bq(cup_shots,   "sofascore_shots",              project_id, bq_dataset)
                    else:
                        save_local({
                            "sofascore_matches":            cup_matches,
                            "sofascore_player_match_stats": cup_players,
                            "sofascore_shots":              cup_shots,
                            "sofascore_team_match_stats":   cup_teams,
                        })
                    total_matches += len(cup_matches)
                    total_players += len(cup_players)
                    total_shots   += len(cup_shots)
                    total_team    += len(cup_teams)

    log.info(
        f"\nSummary: {total_matches} matches | "
        f"{total_players:,} player rows | "
        f"{total_shots:,} shots | "
        f"{total_team:,} team-stat rows"
        + (f" | {total_skipped_players:,} player rows skipped (all-null stats)" if total_skipped_players else "")
    )


if __name__ == "__main__":
    asyncio.run(run_scrape())
