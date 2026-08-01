"""
One-time backfill (+ incremental re-run) building a durable identity crosswalk:
pipeline/dbt/seeds/player_id_map.csv, mapping sofascore_player_id <-> tm_player_id.

Why this exists: gold.agg_scouting_player_season and silver.silver_bqml_wages currently
join SofaScore <-> Transfermarkt on LOWER(TRIM(player_name)) [+ club name], which both
misses matches for accent/diacritic differences and, worse, silently merges two different
people who share a name. TM's own player_id is a permanent per-person ID (scraped from
the /profil/spieler/{id} URL, stable across clubs/seasons), and SofaScore's player_id is
similarly stable per person -- so a single static (sofascore_id, tm_id) pair, once
confirmed, never needs to be re-derived even after the player transfers clubs.

Matching strategy (mirrors the manual-review pattern already used in club_name_aliases.csv):
  1. Club-bridge candidates: for each SofaScore player, look at every team_id they've
     played for (across all scraped seasons), map each to a tm_club_id via
     club_name_aliases.csv (built by build_team_id_map.py), and fuzzy-match their name
     only against TM players who were ever listed at one of those bridged clubs. This is
     the trustworthy path -- club affiliation is independent corroboration, not just a
     name string coincidence.
  2. Fallback: if no club bridge exists (player's club isn't aliased, or TM has no
     snapshot for that club), fuzzy-match the name against the *entire* TM player pool.
     This has no independent corroboration, so it's always flagged manual_confirm
     regardless of score.
  3. Auto-accept: club-bridge match with score >= AUTO_ACCEPT_SCORE and a clear margin
     over the second-best candidate. Everything else is manual_confirm and should be
     spot-checked before being trusted for anything financially/scouting sensitive.

Run locally:
    python3 pipeline/scripts/build_player_id_map.py [--dry-run]
"""

import argparse
import csv
import logging
from collections import defaultdict
from datetime import date
from pathlib import Path

from google.cloud import bigquery
from rapidfuzz import fuzz, process

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("build_player_id_map")

PROJECT = "real-zaragoza-500608"
SEEDS_DIR = Path(__file__).resolve().parents[1] / "dbt" / "seeds"
ALIASES_CSV = SEEDS_DIR / "club_name_aliases.csv"
OUT_CSV = SEEDS_DIR / "player_id_map.csv"

AUTO_ACCEPT_SCORE = 92
AUTO_ACCEPT_MARGIN = 8  # best score must beat 2nd-best candidate by this many points
MIN_CANDIDATE_SCORE = 65  # below this, "no match" is more honest than a wrong guess
MIN_LENGTH_RATIO = 0.5    # reject candidates whose name is <50% the length of the other
                          # (kills WRatio partial-match false positives on TM nicknames,
                          # e.g. "Gabriel Magalhaes" scoring 90 against unrelated "Maga")


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _length_ok(a: str, b: str) -> bool:
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return False
    return min(la, lb) / max(la, lb) >= MIN_LENGTH_RATIO


def load_team_bridge() -> dict[str, str]:
    """sofascore_team_id -> tm_club_id, from the ID-augmented alias seed."""
    bridge = {}
    with open(ALIASES_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sofa_id, tm_id = row.get("sofascore_team_id"), row.get("tm_club_id")
            if sofa_id and tm_id:
                bridge[sofa_id] = tm_id
    log.info(f"Loaded {len(bridge)} sofascore_team_id -> tm_club_id bridge pairs")
    return bridge


def load_sofascore_players(client: bigquery.Client) -> list[dict]:
    query = f"""
        SELECT
          player_id,
          ANY_VALUE(player_name) AS player_name,
          ARRAY_AGG(DISTINCT team_id IGNORE NULLS) AS team_ids
        FROM `{PROJECT}.silver.player_stats`
        WHERE player_id IS NOT NULL AND player_name IS NOT NULL
        GROUP BY player_id
    """
    rows = [dict(r) for r in client.query(query).result()]
    log.info(f"Loaded {len(rows)} distinct SofaScore players")
    return rows


def load_tm_players(client: bigquery.Client) -> list[dict]:
    query = f"""
        SELECT
          player_id,
          ANY_VALUE(name) AS name,
          ARRAY_AGG(DISTINCT club_id IGNORE NULLS) AS club_ids
        FROM `{PROJECT}.silver.tm_players`
        WHERE player_id IS NOT NULL AND name IS NOT NULL
        GROUP BY player_id
    """
    rows = [dict(r) for r in client.query(query).result()]
    log.info(f"Loaded {len(rows)} distinct TM players")
    return rows


def build_club_to_tm_players(tm_players: list[dict]) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = defaultdict(list)
    for p in tm_players:
        for club_id in p["club_ids"]:
            idx[club_id].append(p)
    return idx


def match_one(sofa_name: str, candidates: list[dict]) -> tuple[dict | None, float, float]:
    """Return (best_candidate, best_score, second_best_score) from a small candidate list.
    Candidates whose name length is wildly different from sofa_name are dropped first --
    otherwise WRatio's partial-match component happily scores a short nickname substring
    (e.g. "Maga") very high against an unrelated full name."""
    length_ok_candidates = [c for c in candidates if _length_ok(sofa_name, c["name"])]
    if not length_ok_candidates:
        return None, 0.0, 0.0
    scored = sorted(
        ((c, fuzz.WRatio(sofa_name, c["name"])) for c in length_ok_candidates),
        key=lambda t: t[1],
        reverse=True,
    )
    best_c, best_s = scored[0]
    second_s = scored[1][1] if len(scored) > 1 else 0.0
    if best_s < MIN_CANDIDATE_SCORE:
        return None, 0.0, 0.0
    return best_c, best_s, second_s


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    client = bigquery.Client(project=PROJECT)
    team_bridge = load_team_bridge()
    sofascore_players = load_sofascore_players(client)
    tm_players = load_tm_players(client)
    club_to_tm = build_club_to_tm_players(tm_players)
    tm_name_pool = [(p["name"], p) for p in tm_players]

    today = date.today().isoformat()
    out_rows = []
    n_bridge_auto = n_bridge_manual = n_fallback = n_unmatched = 0

    for i, sp in enumerate(sofascore_players):
        if i and i % 3000 == 0:
            log.info(f"  ... {i}/{len(sofascore_players)} processed")

        sofa_name = sp["player_name"]
        candidate_club_ids = {team_bridge[t] for t in sp["team_ids"] if t in team_bridge}
        candidates = []
        seen_ids = set()
        for cid in candidate_club_ids:
            for c in club_to_tm.get(cid, []):
                if c["player_id"] not in seen_ids:
                    candidates.append(c)
                    seen_ids.add(c["player_id"])

        best_c = None
        if candidates:
            best_c, best_s, second_s = match_one(sofa_name, candidates)
            if best_c is not None:
                if best_s >= AUTO_ACCEPT_SCORE and (best_s - second_s) >= AUTO_ACCEPT_MARGIN:
                    method = "club_bridge_auto"
                    n_bridge_auto += 1
                else:
                    method = "club_bridge_manual_confirm"
                    n_bridge_manual += 1
                out_rows.append({
                    "sofascore_player_id": sp["player_id"],
                    "sofascore_player_name": sofa_name,
                    "tm_player_id": best_c["player_id"],
                    "tm_player_name": best_c["name"],
                    "match_score": round(best_s, 1),
                    "match_method": method,
                    "matched_at": today,
                })
                continue

        # Fallback: no club bridge (or club-bridge candidates all filtered out) -- global
        # name search, always manual_confirm. Length-ratio filter applied post-hoc since
        # process.extractOne can't take a per-candidate predicate with score_cutoff.
        result = process.extractOne(
            sofa_name, [n for n, _ in tm_name_pool], scorer=fuzz.WRatio, score_cutoff=90
        )
        if result and not _length_ok(sofa_name, result[0]):
            result = None
        if result:
            match_name, score, idx = result
            tm_p = tm_name_pool[idx][1]
            out_rows.append({
                "sofascore_player_id": sp["player_id"],
                "sofascore_player_name": sofa_name,
                "tm_player_id": tm_p["player_id"],
                "tm_player_name": tm_p["name"],
                "match_score": round(score, 1),
                "match_method": "name_only_fallback_manual_confirm",
                "matched_at": today,
            })
            n_fallback += 1
        else:
            n_unmatched += 1

    log.info(
        f"Done: {n_bridge_auto} club-bridge auto-accepted, {n_bridge_manual} club-bridge "
        f"needing manual confirm, {n_fallback} name-only fallback (manual confirm), "
        f"{n_unmatched} no candidate found at all."
    )
    log.info(f"Total mapped: {len(out_rows)}/{len(sofascore_players)} "
              f"({len(out_rows)/len(sofascore_players)*100:.1f}%)")

    if args.dry_run:
        log.info("--dry-run: not writing CSV")
        return

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "sofascore_player_id", "sofascore_player_name", "tm_player_id", "tm_player_name",
            "match_score", "match_method", "matched_at",
        ])
        writer.writeheader()
        writer.writerows(out_rows)
    log.info(f"Wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
