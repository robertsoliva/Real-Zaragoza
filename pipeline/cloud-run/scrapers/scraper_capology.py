"""
Capology wage scraper — extracts reported gross wages from capology.com
and loads them into BigQuery raw.capology_wages.

Covers top 5 EU leagues: Premier League, La Liga, Bundesliga, Ligue 1, Serie A.
Rate limited to 1.5 s between leagues. Raw HTML cached on disk per run date.

Usage:
    python scraper_capology.py [--force] [--dry-run]

Environment:
    GCP_PROJECT_ID   BigQuery project (default: real-zaragoza-500608)
    BQ_DATASET       BigQuery dataset  (default: raw)
"""

import argparse
import logging
import os
import re
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

GCP_PROJECT = os.environ.get("GCP_PROJECT_ID", "real-zaragoza-500608")
BQ_DATASET = os.environ.get("BQ_DATASET", "raw")
BQ_TABLE = "capology_wages"

RAW_DIR = Path(__file__).resolve().parent / "capology_cache"
REQUEST_TIMEOUT = 20
RATE_LIMIT_SECONDS = 1.5
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

LEAGUES = [
    {"name": "Premier League",  "url": "https://www.capology.com/uk/premier-league/salaries/",  "tier": 1},
    {"name": "La Liga",         "url": "https://www.capology.com/es/la-liga/salaries/",         "tier": 1},
    {"name": "Bundesliga",      "url": "https://www.capology.com/de/1-bundesliga/salaries/",    "tier": 1},
    {"name": "Ligue 1",         "url": "https://www.capology.com/fr/ligue-1/salaries/",         "tier": 1},
    {"name": "Serie A",         "url": "https://www.capology.com/it/serie-a/salaries/",         "tier": 1},
]

_POS_MAP = {"F": "ATT", "M": "MID", "D": "DEF", "GK": "GK"}

_RE_NAME       = re.compile(r"'name':\s*\"<a[^>]+>[^>]+>([^<]+)</a>\"")
_RE_ANNUAL_EUR = re.compile(r"'annual_gross_eur':\s*accounting\.formatMoney\(\"(\d+)\"")
_RE_POSITION   = re.compile(r"'position':\s*\"([^\"]+)\"")
_RE_POS_DETAIL = re.compile(r"'position_detail':\s*\"([^\"]+)\"")
_RE_AGE        = re.compile(r"'age':\s*Math\.round\(\"(\d+)\"\)")
_RE_CLUB       = re.compile(r"'club':\s*\"<a[^>]+>([^<]+)</a>\"")
_RE_COUNTRY    = re.compile(r"'country':\s*\"([^\"]+)\"")
_RE_ACTIVE     = re.compile(r"'active':\s*\"([^\"]+)\"")
_RE_LOAN       = re.compile(r"'loan':\s*\"([^\"]+)\"")

BQ_SCHEMA = [
    bigquery.SchemaField("player_name",      "STRING",  description="Full player name as shown on Capology"),
    bigquery.SchemaField("primary_position", "STRING",  description="Detailed position (e.g. Centre-Back, Left Winger) from Capology"),
    bigquery.SchemaField("position_group",   "STRING",  description="Broad position group: ATT, MID, DEF, or GK"),
    bigquery.SchemaField("age",              "INTEGER", description="Player age at time of scrape"),
    bigquery.SchemaField("club_name",        "STRING",  description="Current club name"),
    bigquery.SchemaField("nationality",      "STRING",  description="Player nationality / country code"),
    bigquery.SchemaField("league_name",      "STRING",  description="League name (e.g. Premier League, La Liga)"),
    bigquery.SchemaField("league_tier",      "INTEGER", description="League tier: 1 = top division"),
    bigquery.SchemaField("wage_eur_weekly",  "FLOAT",   description="Reported gross weekly wage in EUR (annual / 52)"),
    bigquery.SchemaField("active",           "BOOLEAN", description="Whether the player is currently active"),
    bigquery.SchemaField("on_loan",          "BOOLEAN", description="True if the player is on loan at this club"),
    bigquery.SchemaField("ingested_date",    "DATE",    description="Date the data was scraped from Capology"),
]


def _fetch(url: str) -> str:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.text
        except requests.HTTPError as e:
            raise RuntimeError(f"HTTP {e.response.status_code} for {url}") from e
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Network error after {MAX_RETRIES} tries: {e}") from e
            wait = 2 ** attempt
            logger.warning("Attempt %d failed (%s), retrying in %ds…", attempt, e, wait)
            time.sleep(wait)


def _fetch_with_cache(name: str, url: str, force: bool) -> str:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    slug = name.lower().replace(" ", "_")
    cache_file = RAW_DIR / f"capology_{slug}_{date.today()}.html"
    if cache_file.exists() and not force:
        logger.info("  Using cached HTML: %s", cache_file.name)
        return cache_file.read_text(encoding="utf-8")
    html = _fetch(url)
    cache_file.write_text(html, encoding="utf-8")
    return html


def _parse_block(block: str) -> dict | None:
    name       = (m := re.search(_RE_NAME, block)) and m.group(1)
    annual_eur = (m := re.search(_RE_ANNUAL_EUR, block)) and m.group(1)
    position   = (m := re.search(_RE_POSITION, block)) and m.group(1)
    pos_detail = (m := re.search(_RE_POS_DETAIL, block)) and m.group(1)
    age        = (m := re.search(_RE_AGE, block)) and m.group(1)
    club       = (m := re.search(_RE_CLUB, block)) and m.group(1)
    country    = (m := re.search(_RE_COUNTRY, block)) and m.group(1)
    active     = (m := re.search(_RE_ACTIVE, block)) and m.group(1)
    loan       = (m := re.search(_RE_LOAN, block)) and m.group(1)

    if not name or not annual_eur:
        return None
    wage = float(annual_eur)
    if wage <= 0:
        return None

    return {
        "player_name":      name.strip(),
        "primary_position": pos_detail or position or "",
        "position_group":   _POS_MAP.get(position or "", "MID"),
        "age":              int(age) if age else None,
        "club_name":        club.strip() if club else "",
        "nationality":      country or "",
        "wage_eur_weekly":  round(wage / 52, 2),
        "active":           active == "True",
        "on_loan":          loan == "True",
    }


def scrape_league(league: dict, force: bool) -> pd.DataFrame:
    html = _fetch_with_cache(league["name"], league["url"], force)
    soup = BeautifulSoup(html, "html.parser")
    script_text = None
    for tag in soup.find_all("script"):
        if "var data = [" in tag.get_text():
            script_text = tag.get_text()
            break
    if not script_text:
        raise RuntimeError(f"No `var data = [...]` found for {league['name']}")

    start = script_text.index("var data = [") + len("var data = [")
    end = script_text.index("];", start)
    blocks = re.split(r"\},\s*\{", script_text[start:end])

    records = []
    for i, block in enumerate(blocks):
        try:
            r = _parse_block(block)
            if r:
                records.append(r)
        except Exception as e:
            logger.debug("Skipping block %d in %s: %s", i, league["name"], e)

    df = pd.DataFrame(records)
    df["league_name"] = league["name"]
    df["league_tier"] = league["tier"]
    df["ingested_date"] = str(date.today())
    logger.info("  %s → %d players", league["name"], len(df))
    return df


def write_to_bq(df: pd.DataFrame) -> None:
    client = bigquery.Client(project=GCP_PROJECT)
    table_ref = f"{GCP_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"

    job_config = bigquery.LoadJobConfig(
        schema=BQ_SCHEMA,
        write_disposition="WRITE_APPEND",
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    records = df.where(pd.notna(df), None).to_dict(orient="records")
    job = client.load_table_from_json(records, table_ref, job_config=job_config)
    job.result()
    logger.info("Inserted %d rows into %s", len(df), table_ref)


def main():
    parser = argparse.ArgumentParser(description="Capology wage scraper → BigQuery")
    parser.add_argument("--force", action="store_true", help="Re-download HTML even if cached")
    parser.add_argument("--dry-run", action="store_true", help="Scrape but do not write to BQ")
    args = parser.parse_args()

    all_frames = []
    failures = []

    for league in LEAGUES:
        logger.info("=== Scraping %s ===", league["name"])
        try:
            df = scrape_league(league, force=args.force)
            all_frames.append(df)
        except Exception as e:
            logger.error("Failed: %s — %s", league["name"], e)
            failures.append(league["name"])
        time.sleep(RATE_LIMIT_SECONDS)

    if not all_frames:
        raise RuntimeError(f"All leagues failed: {failures}")
    if failures:
        logger.warning("Partial scrape — skipped: %s", failures)

    combined = pd.concat(all_frames, ignore_index=True)
    logger.info("Total: %d rows across %d leagues", len(combined), len(all_frames))

    if args.dry_run:
        logger.info("Dry run — not writing to BQ. Sample:\n%s", combined.head())
        return

    write_to_bq(combined)
    logger.info("Done.")


if __name__ == "__main__":
    main()
