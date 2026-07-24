"""
Real Zaragoza — multi-league Transfermarkt scraper.

For each active pipeline league, discovers all clubs from the competition
startseite page, then scrapes each club's /plus/1 squad page. Results are
appended to raw.transfermarkt_players in BigQuery (separate from the
single-club raw.transfermarkt_squad table).

Usage:
    python scraper_transfermarkt_leagues.py               # all leagues
    python scraper_transfermarkt_leagues.py --league L2   # one league (tm_code)
    python scraper_transfermarkt_leagues.py --dry-run     # print clubs, skip player scrape

Rate limiting:
    4 s between club requests, 10 s between leagues.
    Retry once on non-200 before skipping with WARNING.
"""

import argparse
import logging
import math
import os
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import pandas as pd
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── League registry ────────────────────────────────────────────────────────────
# (sofascore_id, tm_code, tm_slug, league_name, tm_season)
# TM codes verified 2026-07-24 against live Transfermarkt pages.
LEAGUES = [
    (54,    "ES2",   "segunda-division",            "LaLiga2",               2025),
    (53,    "IT2",   "serie-b",                     "Serie B",               2025),
    (182,   "FR2",   "ligue-2",                     "Ligue 2",               2025),
    (52,    "TR1",   "super-lig",                   "Turkish Süper Lig",     2025),
    (45,    "A1",    "bundesliga",                  "Austrian Bundesliga",   2025),
    (152,   "RO1",   "liga-1",                      "Romanian SuperLiga",    2025),
    (196,   "JAP1",  "j1-league",                   "J1 League",             2025),
    (20,    "NO1",   "eliteserien",                 "Norwegian Eliteserien", 2025),
    (410,   "RSK1",  "k-league-1",                  "Korean K League 1",     2025),
    (390,   "BRA2",  "serie-b",                     "Brasileirao Serie B",   2024),
    (210,   "SER1",  "super-liga",                  "Mozzart Bet Superliga", 2025),
    (242,   "MLS1",  "major-league-soccer",         "MLS",                   2025),
    (40,    "SE1",   "allsvenskan",                 "Allsvenskan",           2025),
    (131,   "NL2",   "eerste-divisie",              "Eerste Divisie",        2025),
    (685,   "MO1N",  "divizia-nationala",           "Moldovan Super Liga",   2025),
    (37,    "NL1",   "eredivisie",                  "Eredivisie",            2025),
    (38,    "BE1",   "jupiler-pro-league",           "Belgian Pro League",    2025),
    (238,   "PO1",   "liga-portugal",               "Liga Portugal",         2025),
    (35,    "L2",    "2-bundesliga",                "2. Bundesliga",         2025),
    # 1RFEF (17073) intentionally excluded — too many teams for automated batch scrape
]

BASE_URL = "https://www.transfermarkt.es"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

# ── HTTP helpers ───────────────────────────────────────────────────────────────

def get_soup(url: str) -> Optional[BeautifulSoup]:
    """Fetch URL with one retry on failure. Returns None if both attempts fail."""
    for attempt in range(2):
        try:
            log.info(f"GET {url}")
            r = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
            if r.status_code == 200:
                return BeautifulSoup(r.content, "html.parser")
            log.warning(f"Non-200 response {r.status_code} for {url} (attempt {attempt + 1})")
        except Exception as exc:
            log.warning(f"Request error for {url} (attempt {attempt + 1}): {exc}")
        if attempt == 0:
            time.sleep(3)
    log.warning(f"Skipping {url} after 2 failed attempts")
    return None


# ── Value parsers (same logic as scraper_transfermarkt.py) ────────────────────

def parse_market_value(raw: str) -> Optional[int]:
    """
    Normalise Spanish Transfermarkt value strings to integer EUR.
    '200 mil €' -> 200_000
    '1,20 mill. €' -> 1_200_000
    """
    if not raw:
        return None
    v = raw.strip()
    if v in ("-", "0", "", "€0"):
        return 0
    if "mill." in v:
        num = v.replace("mill.", "").replace("€", "").replace(" ", "").replace(",", ".")
        try:
            return int(float(num) * 1_000_000)
        except ValueError:
            pass
    elif "mil" in v:
        num = v.replace("mil", "").replace("€", "").replace(" ", "").replace(",", ".")
        try:
            return int(float(num) * 1_000)
        except ValueError:
            pass
    v2 = v.replace("€", "").replace(",", ".").strip()
    try:
        if v2.endswith("m"):
            return int(float(v2[:-1]) * 1_000_000)
        if v2.endswith("k"):
            return int(float(v2[:-1]) * 1_000)
        return int(float(v2))
    except ValueError:
        log.warning(f"Could not parse market value: {raw!r}")
        return None


def parse_tm_date(raw: str) -> Optional[str]:
    """'DD/MM/YYYY' -> 'YYYY-MM-DD' for BigQuery DATE fields."""
    if not raw or raw.strip() in ("-", ""):
        return None
    try:
        return datetime.strptime(raw.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


# ── Club discovery ─────────────────────────────────────────────────────────────

def discover_clubs(tm_code: str, tm_slug: str, season: int) -> list[dict]:
    """
    Scrape the competition startseite page and return a list of club dicts:
      [{"club_id": "142", "club_slug": "real-zaragoza", "club_name": "Real Zaragoza"}, ...]
    """
    url = f"{BASE_URL}/{tm_slug}/startseite/wettbewerb/{tm_code}/saison_id/{season}"
    soup = get_soup(url)
    if soup is None:
        return []

    clubs = []
    seen_ids = set()

    # Club links are in <td class="hauptlink no-border-links"><a href="/slug/startseite/verein/ID/...">
    for td in soup.find_all("td", class_="hauptlink no-border-links"):
        a = td.find("a", href=re.compile(r"/startseite/verein/\d+"))
        if not a:
            continue
        href = a["href"]  # e.g. /real-zaragoza/startseite/verein/142/saison_id/2025
        m = re.search(r"/startseite/verein/(\d+)", href)
        if not m:
            continue
        club_id = m.group(1)
        if club_id in seen_ids:
            continue
        seen_ids.add(club_id)

        # Extract slug — first path segment of href
        slug_match = re.match(r"/([^/]+)/", href)
        club_slug = slug_match.group(1) if slug_match else href.split("/")[1]
        club_name = a.get_text(strip=True)

        clubs.append({
            "club_id":   club_id,
            "club_slug": club_slug,
            "club_name": club_name,
        })

    log.info(f"[{tm_code}] Discovered {len(clubs)} clubs")
    return clubs


# ── Squad scraper ──────────────────────────────────────────────────────────────

def scrape_squad(
    club_slug: str,
    club_id: str,
    club_name: str,
    tm_league_code: str,
    league_name: str,
    season: int,
) -> pd.DataFrame:
    """
    Fetch the /plus/1 squad page for a single club and return a DataFrame
    with one row per player, including the 5 league/club context columns.
    """
    url = f"{BASE_URL}/{club_slug}/kader/verein/{club_id}/saison_id/{season}/plus/1"
    soup = get_soup(url)
    if soup is None:
        return pd.DataFrame()

    # ── Player names ───────────────────────────────────────────────────────────
    names = [
        img.get("title", "").strip()
        for img in soup.find_all("img", {"class": "bilderrahmen-fixed lazy lazy"})
    ]

    # ── Player IDs + positions ─────────────────────────────────────────────────
    player_ids = []
    positions  = []
    for cell in soup.find_all("td", {"class": "posrela"}):
        link = cell.find("a", href=re.compile(r"/profil/spieler/\d+"))
        if link:
            m = re.search(r"/spieler/(\d+)", link["href"])
            player_ids.append(m.group(1) if m else None)
        else:
            player_ids.append(None)

        rows = cell.find_all("tr")
        positions.append(rows[1].find("td").text.strip() if len(rows) > 1 else None)

    # ── Columnar stats (8 td.zentriert per player row) ────────────────────────
    stats = soup.find_all("td", {"class": "zentriert"})

    jersey_numbers = [
        s.find("div", class_="rn_nummer").text.strip()
        if s.find("div", class_="rn_nummer") else None
        for s in stats[0::8]
    ]

    raw_ages = [s.get_text(" ", strip=True) for s in stats[1::8]]
    ages = []
    dobs  = []
    for raw in raw_ages:
        m = re.search(r"\((\d+)\)", raw)
        ages.append(int(m.group(1)) if m else None)
        d = re.search(r"(\d{2}/\d{2}/\d{4})", raw)
        dobs.append(parse_tm_date(d.group(1)) if d else None)

    nationalities = [
        s.find("img").get("title") if s.find("img") else None
        for s in stats[2::8]
    ]
    nationalities_all = [
        ", ".join(img.get("title", "") for img in s.find_all("img"))
        for s in stats[2::8]
    ]

    heights      = [s.get_text(strip=True) for s in stats[3::8]]
    foots        = [s.get_text(strip=True) for s in stats[4::8]]
    joined_dates = [s.get_text(strip=True) for s in stats[5::8]]

    signing_cells = stats[6::8]
    signed_from  = []
    signing_fees = []
    for td in signing_cells:
        a = td.find("a")
        if a:
            title = a.get("title", "")
            if ": Ablöse " in title:
                parts = title.split(": Ablöse ")
                signed_from.append(parts[0])
                signing_fees.append(parts[1])
            else:
                img = td.find("img")
                signed_from.append(img.get("title") if img else a.get("title"))
                signing_fees.append(None)
        else:
            signed_from.append(None)
            signing_fees.append(None)

    contract_expiries = [s.get_text(strip=True) for s in stats[7::8]]

    raw_values = [
        td.find("a").text.strip() if td.find("a") else "€0"
        for td in soup.find_all("td", {"class": "rechts hauptlink"})
    ]

    # ── Assemble rows ──────────────────────────────────────────────────────────
    today       = date.today().isoformat()
    ingested_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    n = min(len(names), len(player_ids), len(jersey_numbers), len(ages),
            len(nationalities), len(positions))
    if n < len(names):
        log.warning(f"[{club_name}] List lengths diverged — truncating to {n} players")

    def _get(lst, i):
        return lst[i] if i < len(lst) else None

    rows = []
    for i in range(n):
        rows.append({
            "ingested_date":    today,
            "season_id":        season,
            "player_id":        _get(player_ids, i),
            "name":             _get(names, i),
            "date_of_birth":    _get(dobs, i),
            "jersey_number":    _get(jersey_numbers, i),
            "position":         _get(positions, i),
            "age":              _get(ages, i),
            "nationality":      _get(nationalities, i),
            "nationality_all":  _get(nationalities_all, i),
            "height":           _get(heights, i),
            "foot":             _get(foots, i),
            "joined_date":      parse_tm_date(_get(joined_dates, i)),
            "signed_from":      _get(signed_from, i),
            "signing_fee":      _get(signing_fees, i),
            "contract_expiry":  parse_tm_date(_get(contract_expiries, i)),
            "market_value_eur": parse_market_value(_get(raw_values, i)),
            "ingested_at":      ingested_at,
            # League/club context
            "club_id":          club_id,
            "club_slug":        club_slug,
            "club_name":        club_name,
            "tm_league_code":   tm_league_code,
            "league_name":      league_name,
        })

    df = pd.DataFrame(rows)
    log.info(f"[{tm_league_code}] {club_name}: {len(df)} players")
    return df


# ── Output ─────────────────────────────────────────────────────────────────────

def save_local(df: pd.DataFrame, tm_code: str, season: int) -> Path:
    """Write CSV to data/raw/transfermarkt/leagues/ for local inspection."""
    out_dir = Path(__file__).parents[3] / "data" / "raw" / "transfermarkt" / "leagues"
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"players_{tm_code}_{season}_{date.today().isoformat()}.csv"
    out_path = out_dir / fname
    df.to_csv(out_path, index=False)
    log.info(f"Saved locally -> {out_path}")
    return out_path


def write_to_bq(df: pd.DataFrame, project_id: str) -> None:
    """Append rows to raw.transfermarkt_players in BigQuery."""
    from google.cloud import bigquery

    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.raw.transfermarkt_players"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    df_out = df.copy()
    for col in ["ingested_date", "date_of_birth", "joined_date", "contract_expiry"]:
        if col in df_out.columns:
            df_out[col] = df_out[col].astype(str).replace("None", "").replace("nan", "")

    rows = [
        {k: (None if (isinstance(v, float) and math.isnan(v)) else v)
         for k, v in row.items()}
        for row in df_out.to_dict(orient="records")
    ]
    # Replace empty strings for date fields with None
    date_fields = {"ingested_date", "date_of_birth", "joined_date", "contract_expiry"}
    rows = [
        {k: (None if (k in date_fields and v == "") else v) for k, v in row.items()}
        for row in rows
    ]

    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        raise RuntimeError(f"BQ insert errors: {errors}")
    log.info(f"Inserted {len(rows)} rows -> {table_ref}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-league Transfermarkt scraper")
    parser.add_argument(
        "--league", metavar="TM_CODE",
        help="Scrape only this league (Transfermarkt code, e.g. L2)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Discover clubs only — do not scrape player squads"
    )
    args = parser.parse_args()

    # Filter league list
    leagues = LEAGUES
    if args.league:
        leagues = [lg for lg in LEAGUES if lg[1] == args.league]
        if not leagues:
            log.error(f"Unknown league code: {args.league!r}. "
                      f"Valid codes: {[lg[1] for lg in LEAGUES]}")
            raise SystemExit(1)

    project_id = os.environ.get("GCP_PROJECT_ID")

    all_frames = []
    for idx, (ss_id, tm_code, tm_slug, league_name, tm_season) in enumerate(leagues):
        if idx > 0:
            log.info(f"Sleeping 10s between leagues...")
            time.sleep(10)

        log.info(f"=== League: {league_name} ({tm_code}) season {tm_season} ===")
        clubs = discover_clubs(tm_code, tm_slug, tm_season)
        if not clubs:
            log.warning(f"No clubs found for {tm_code} — skipping")
            continue

        if args.dry_run:
            for c in clubs:
                print(f"  {tm_code} | {c['club_name']:40s} | id={c['club_id']} | slug={c['club_slug']}")
            continue

        for club_idx, club in enumerate(clubs):
            if club_idx > 0:
                log.info("Sleeping 4s between clubs...")
                time.sleep(4)
            df = scrape_squad(
                club_slug=club["club_slug"],
                club_id=club["club_id"],
                club_name=club["club_name"],
                tm_league_code=tm_code,
                league_name=league_name,
                season=tm_season,
            )
            if df.empty:
                continue
            all_frames.append(df)

        # Write per-league after each league completes (fail-safe against mid-run crash)
        if all_frames and not args.dry_run:
            combined = pd.concat(all_frames, ignore_index=True)
            if project_id:
                write_to_bq(combined, project_id)
            else:
                save_local(combined, tm_code, tm_season)
            all_frames = []  # reset after writing

    if args.dry_run:
        log.info("Dry-run complete.")
        return

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        if project_id:
            write_to_bq(combined, project_id)
        else:
            log.info("GCP_PROJECT_ID not set — saving locally")
            for (_, tm_code, _, _, tm_season) in leagues:
                save_local(combined, tm_code, tm_season)

    log.info("All leagues processed.")


if __name__ == "__main__":
    main()
