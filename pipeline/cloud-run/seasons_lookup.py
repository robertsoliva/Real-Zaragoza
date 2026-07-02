"""
Helper: list all available SofaScore seasons for one or more tournaments.

Usage:
  python seasons_lookup.py 53 182 152 196
  python seasons_lookup.py          # prompts for a single tournament ID

Run this to find season IDs when adding a new league to the scraper.
"""

import asyncio
import sys

from curl_cffi.requests import AsyncSession

BASE_URL = "https://api.sofascore.com"
HEADERS = {
    "Accept": "application/json",
    "Referer": "https://www.sofascore.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}

LEAGUE_NAMES = {
    "54":    "LaLiga2",
    "17073": "1RFEF",
    "53":    "Serie B",
    "182":   "Ligue 2",
    "152":   "Romanian SuperLiga",
    "196":   "J1 League",
}


async def get_seasons(session: AsyncSession, tournament_id: str) -> None:
    name = LEAGUE_NAMES.get(tournament_id, f"tournament_{tournament_id}")
    url  = f"{BASE_URL}/api/v1/unique-tournament/{tournament_id}/seasons"
    resp = await session.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        print(f"  [{tournament_id}] {name}: HTTP {resp.status_code}")
        return
    seasons = resp.json().get("seasons") or []
    print(f"\n{name} (tournament_id={tournament_id}):")
    for s in seasons:
        print(f"  season_id={s.get('id'):<8}  name={s.get('name')}")


async def main(tournament_ids: list[str]) -> None:
    async with AsyncSession(impersonate="chrome124") as session:
        for tid in tournament_ids:
            await get_seasons(session, tid)
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    ids = sys.argv[1:] or [input("Tournament ID: ").strip()]
    asyncio.run(main(ids))
