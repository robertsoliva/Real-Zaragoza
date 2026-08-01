"""
One-off/incremental maintenance script — augments pipeline/dbt/seeds/club_name_aliases.csv
with sofascore_team_id and tm_club_id columns.

Why: club_name_aliases.csv currently maps sofascore_team_name -> tm_club_name as strings.
That's fragile (accents, abbreviations) and every downstream join re-does the string match.
Once both IDs are attached to each alias row, downstream models can join on IDs directly
(sofascore.team_id = map.sofascore_team_id, tm.club_id = map.tm_club_id) instead of names.

Run locally (needs `bq`/application-default credentials already set up for this project):
    python3 pipeline/scripts/build_team_id_map.py [--dry-run]

Safe to re-run: recomputes ID lookups for every alias row each time (idempotent), so it's
also how you'd refresh IDs after a promotion/relegation adds new club rows to the seed.
"""

import argparse
import csv
import logging
from pathlib import Path

from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("build_team_id_map")

PROJECT = "real-zaragoza-500608"
ALIASES_CSV = Path(__file__).resolve().parents[1] / "dbt" / "seeds" / "club_name_aliases.csv"


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def load_sofascore_teams(client: bigquery.Client) -> dict[tuple[str, str], str]:
    """(team_name_norm, league_name_norm) -> team_id. Last-seen team_id wins if ambiguous."""
    query = """
        SELECT team_id, team_name, league_name FROM (
          SELECT home_team_id AS team_id, home_team_name AS team_name, league_name FROM `{p}.silver.matches`
          UNION ALL
          SELECT away_team_id, away_team_name, league_name FROM `{p}.silver.matches`
        )
        WHERE team_id IS NOT NULL AND team_name IS NOT NULL
    """.format(p=PROJECT)
    out: dict[tuple[str, str], str] = {}
    dupes = set()
    for row in client.query(query).result():
        key = (_norm(row.team_name), _norm(row.league_name))
        if key in out and out[key] != row.team_id:
            dupes.add(key)
        out[key] = row.team_id
    if dupes:
        log.warning(f"{len(dupes)} (team_name, league_name) pairs map to >1 sofascore team_id — "
                     f"likely a club renamed mid-history or a genuine name collision. Spot-check these.")
    log.info(f"Loaded {len(out)} distinct SofaScore (team_name, league_name) -> team_id pairs")
    return out


def load_tm_clubs(client: bigquery.Client) -> dict[tuple[str, str], str]:
    """(club_name_norm, league_name_norm) -> club_id."""
    query = f"""
        SELECT DISTINCT club_id, club_name, league_name
        FROM `{PROJECT}.silver.tm_players`
        WHERE club_id IS NOT NULL AND club_name IS NOT NULL
    """
    out: dict[tuple[str, str], str] = {}
    dupes = set()
    for row in client.query(query).result():
        key = (_norm(row.club_name), _norm(row.league_name))
        if key in out and out[key] != row.club_id:
            dupes.add(key)
        out[key] = row.club_id
    if dupes:
        log.warning(f"{len(dupes)} (club_name, league_name) pairs map to >1 TM club_id — spot-check these.")
    log.info(f"Loaded {len(out)} distinct TM (club_name, league_name) -> club_id pairs")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print coverage stats, don't write the CSV")
    args = parser.parse_args()

    client = bigquery.Client(project=PROJECT)
    sofascore_teams = load_sofascore_teams(client)
    tm_clubs = load_tm_clubs(client)

    with open(ALIASES_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    n_sofa_matched = n_tm_matched = 0
    unresolved_sofa = []
    unresolved_tm = []

    for row in rows:
        sofa_key = (_norm(row["sofascore_team_name"]), _norm(row["league_name"]))
        tm_key = (_norm(row["tm_club_name"]), _norm(row["league_name"]))

        team_id = sofascore_teams.get(sofa_key, "")
        club_id = tm_clubs.get(tm_key, "")

        row["sofascore_team_id"] = team_id
        row["tm_club_id"] = club_id

        if team_id:
            n_sofa_matched += 1
        else:
            unresolved_sofa.append(f'{row["sofascore_team_name"]} / {row["league_name"]}')
        if club_id:
            n_tm_matched += 1
        else:
            unresolved_tm.append(f'{row["tm_club_name"]} / {row["league_name"]}')

    n = len(rows)
    log.info(f"SofaScore team_id resolved: {n_sofa_matched}/{n} ({n_sofa_matched/n*100:.1f}%)")
    log.info(f"TM club_id resolved:        {n_tm_matched}/{n} ({n_tm_matched/n*100:.1f}%)")

    if unresolved_sofa:
        log.warning(f"{len(unresolved_sofa)} rows with no SofaScore team_id match (first 15):")
        for x in unresolved_sofa[:15]:
            log.warning(f"  - {x}")
    if unresolved_tm:
        log.warning(f"{len(unresolved_tm)} rows with no TM club_id match (first 15):")
        for x in unresolved_tm[:15]:
            log.warning(f"  - {x}")

    if args.dry_run:
        log.info("--dry-run: not writing CSV")
        return

    fieldnames = list(rows[0].keys())  # includes the two new columns since we set them above
    with open(ALIASES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    log.info(f"Wrote {ALIASES_CSV}")


if __name__ == "__main__":
    main()
