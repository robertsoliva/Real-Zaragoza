"""
Real Zaragoza — Transfermarkt squad scraper.

Scrapes the detailed squad page (/plus/1) for verein/142 and outputs one row
per player, aligned to the rz_raw.transfermarkt_squad BigQuery schema.

Local usage:
    python scraper_transfermarkt.py
    → writes data/raw/transfermarkt/squad_<date>.csv

Cloud Run usage (later):
    Publishes a JSON-newlines payload to Pub/Sub for the BQ loader to consume.
"""

import json
import logging
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

# ── Config ────────────────────────────────────────────────────────────────────

CLUB_SLUG = "real-zaragoza"
CLUB_ID   = "142"
SEASON_ID = 2025          # Transfermarkt season ID (year season starts)
BASE_URL  = "https://www.transfermarkt.es"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_soup(url: str) -> BeautifulSoup:
    log.info(f"GET {url}")
    r = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
    r.raise_for_status()
    return BeautifulSoup(r.content, "html.parser")


def parse_market_value(raw: str) -> Optional[int]:
    """
    Normalise Spanish Transfermarkt value strings to integer EUR.
    '200 mil €' → 200_000
    '1,20 mill. €' → 1_200_000  (comma = decimal separator in Spanish)
    '3,00 mill. €' → 3_000_000
    Falls back to English k/m suffixes just in case.
    """
    if not raw:
        return None
    v = raw.strip()
    if v in ("-", "0", "", "€0"):
        return 0
    # Spanish format: 'X,XX mill. €' (millions) or 'X mil €' (thousands)
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
    # English fallback: €Xm / €Xk
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
    """'DD/MM/YYYY' → 'YYYY-MM-DD' for BigQuery DATE fields."""
    if not raw or raw.strip() in ("-", ""):
        return None
    try:
        return datetime.strptime(raw.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None

# ── Scraper ───────────────────────────────────────────────────────────────────

def scrape_squad(
    club_slug: str = CLUB_SLUG,
    club_id: str   = CLUB_ID,
    season: int    = SEASON_ID,
) -> pd.DataFrame:
    """
    Fetch the /plus/1 detailed squad page and return a DataFrame
    with one row per player aligned to rz_raw.transfermarkt_squad.

    The /plus/1 view has exactly 8 td.zentriert cells per player row:
        [0] jersey number  (contains div.rn_nummer)
        [1] age
        [2] nationality    (contains img.flaggenrahmen)
        [3] current club   (contains <a> for loan info)
        [4] height
        [5] foot
        [6] joined date
        [7] signed from / signing fee
    """
    url = f"{BASE_URL}/{club_slug}/kader/verein/{club_id}/saison_id/{season}/plus/1"
    soup = get_soup(url)

    # ── Player names (from portrait img title attributes) ──────────────────
    names = [
        img.get("title", "").strip()
        for img in soup.find_all("img", {"class": "bilderrahmen-fixed lazy lazy"})
    ]

    # ── Player IDs + detailed positions (from posrela cells) ───────────────
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

    # ── Columnar stats from td.zentriert ──────────────────────────────────
    # Spanish Transfermarkt /plus/1 layout (8 cells per player row):
    #   [0] jersey number   [1] birthdate+age  [2] nationality  [3] height
    #   [4] foot            [5] joined date    [6] signed from  [7] contract expiry
    stats = soup.find_all("td", {"class": "zentriert"})

    jersey_numbers = [
        s.find("div", class_="rn_nummer").text.strip()
        if s.find("div", class_="rn_nummer") else None
        for s in stats[0::8]
    ]

    # [1] format: "DD/MM/YYYY (AGE)" — extract age integer
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
    # All nationalities for dual nationals — comma-separated
    nationalities_all = [
        ", ".join(img.get("title", "") for img in s.find_all("img"))
        for s in stats[2::8]
    ]

    heights      = [s.get_text(strip=True) for s in stats[3::8]]
    foots        = [s.get_text(strip=True) for s in stats[4::8]]
    joined_dates = [s.get_text(strip=True) for s in stats[5::8]]

    # [6] signed from — img title or a title, fee after "Ablöse"
    signing_cells = stats[6::8]
    signed_from = []
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

    # ── Market values ───────────────────────────────────────────────────────
    raw_values = [
        td.find("a").text.strip() if td.find("a") else "€0"
        for td in soup.find_all("td", {"class": "rechts hauptlink"})
    ]

    # ── Assemble rows ───────────────────────────────────────────────────────
    today = date.today().isoformat()
    ingested_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    # Guard against any list-length divergence
    n = min(len(names), len(player_ids), len(jersey_numbers), len(ages),
            len(nationalities), len(positions))
    if n < len(names):
        log.warning(f"List lengths diverged — truncating to {n} players")

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
        })

    return pd.DataFrame(rows)

# ── Output ────────────────────────────────────────────────────────────────────

def save_local(df: pd.DataFrame) -> Path:
    """Write CSV to data/raw/transfermarkt/ for local dev inspection."""
    out_dir = Path(__file__).parents[2] / "data" / "raw" / "transfermarkt"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"squad_{CLUB_SLUG}_{SEASON_ID}_{date.today().isoformat()}.csv"
    df.to_csv(out_path, index=False)
    log.info(f"Saved → {out_path}")
    return out_path


def to_jsonl(df: pd.DataFrame) -> str:
    """Serialise to JSON-newlines for BQ streaming / Pub/Sub payload."""
    return "\n".join(json.dumps(r, default=str) for r in df.to_dict(orient="records"))

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    log.info(f"Scraping {CLUB_SLUG} verein/{CLUB_ID} season {SEASON_ID}")
    df = scrape_squad()

    log.info(f"Players scraped: {len(df)}")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 160)
    print(df.to_string(index=False))

    save_local(df)


if __name__ == "__main__":
    main()
