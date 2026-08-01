#!/usr/bin/env python3
"""
Daily SofaScore backfill summary email — fires at 22:00 via launchd.

Reads today's slot logs, parses what ran (label, row counts, success/fail),
checks the remaining queue, and sends a plain-text digest to rsolivamachin@gmail.com.

Credentials stored in ~/.realzaragoza/email.conf (not in git):
    GMAIL_USER=rsolivamachin@gmail.com
    GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
    TO_EMAIL=rsolivamachin@gmail.com
"""

import glob
import json
import re
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

QUEUE_FILE = Path(__file__).parent / "sofascore_queue.txt"
CONFIG_FILE = Path.home() / ".realzaragoza" / "email.conf"
LOG_GLOB = "/tmp/sofascore_*_launchd.log"
TM_MATCH_BASELINE_FILE = Path(__file__).parent / "tm_match_baseline.json"
TM_MATCH_PROJECT = "real-zaragoza-500608"
TM_MATCH_REGRESSION_THRESHOLD_PP = 5.0  # flag a league if its match % drops more than this below baseline
TM_MATCH_MIN_SAMPLE = 20                # ignore leagues too small to be a meaningful signal

SLOT_ORDER = ["midnight", "4am", "8am", "noon", "4pm", "8pm"]


def load_config() -> dict:
    config = {}
    with open(CONFIG_FILE) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip()
    required = {"GMAIL_USER", "GMAIL_APP_PASSWORD", "TO_EMAIL"}
    missing = required - config.keys()
    if missing:
        raise RuntimeError(f"Missing keys in {CONFIG_FILE}: {missing}")
    return config


def parse_slot_logs() -> list[dict]:
    """Read each launchd slot log and extract the most recent run's summary."""
    log_files = {Path(p).stem.replace("sofascore_", "").replace("_launchd", ""): p
                 for p in glob.glob(LOG_GLOB)}

    runs = []
    for slot in SLOT_ORDER:
        log_path = log_files.get(slot)
        if not log_path:
            continue

        try:
            content = Path(log_path).read_text()
        except Exception:
            continue

        if "Queue is empty" in content or "Skipping this slot" in content:
            continue

        # Header line: ===  LABEL  [tournament=X season=Y]
        header = re.search(
            r"={10,}\s+(\S+)\s+\[tournament=(\d+) season=(\d+)\]", content
        )
        if not header:
            continue

        label = header.group(1)
        tournament_id = header.group(2)
        season_id = header.group(3)

        success = "Removed from queue:" in content

        # Scraper summary line: "Summary: N matches | N player rows | N shots | N team-stat rows"
        summary_match = re.search(
            r"Summary:\s+(\d+)\s+matches\s+\|\s+([\d,]+)\s+player rows\s+\|\s+([\d,]+)\s+shots",
            content,
        )
        summary = summary_match.group(0).strip() if summary_match else None

        # First error/traceback line (if any)
        error_line = None
        for line in content.splitlines():
            if re.search(r"Error|Traceback|FAIL|403|banned", line, re.IGNORECASE):
                error_line = line.strip()
                break

        runs.append(
            {
                "slot": slot,
                "label": label,
                "tournament_id": tournament_id,
                "season_id": season_id,
                "success": success,
                "summary": summary,
                "error": error_line,
            }
        )

    return runs


def check_tm_match_quality() -> dict:
    """Compare each league's current TM-match rate (gold.agg_scouting_player_season,
    players with >=450 min) against the captured baseline in tm_match_baseline.json.
    Returns {"regressions": [...]} on success, or {"error": "..."} if the check itself
    failed (e.g. no BQ credentials in this environment) -- never raises, since a failed
    quality check shouldn't block the rest of the daily digest from sending."""
    if not TM_MATCH_BASELINE_FILE.exists():
        return {"error": f"No baseline file at {TM_MATCH_BASELINE_FILE}"}

    try:
        baseline = json.loads(TM_MATCH_BASELINE_FILE.read_text())["leagues"]
    except Exception as e:
        return {"error": f"Could not parse baseline file: {e}"}

    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=TM_MATCH_PROJECT)
        query = f"""
            SELECT league_name, COUNT(*) AS n, COUNTIF(tm_player_id IS NOT NULL) AS matched
            FROM `{TM_MATCH_PROJECT}.gold.agg_scouting_player_season`
            WHERE total_minutes >= 450
            GROUP BY league_name
            HAVING COUNT(*) >= {TM_MATCH_MIN_SAMPLE}
        """
        current = {
            row.league_name: row.matched / row.n * 100
            for row in client.query(query).result()
        }
    except Exception as e:
        return {"error": f"BQ query failed: {e}"}

    regressions = []
    for league, base_pct in baseline.items():
        if league.startswith("_"):
            continue
        cur_pct = current.get(league)
        if cur_pct is None:
            continue  # league not present today (renamed, or below min sample) -- not a regression signal
        drop = base_pct - cur_pct
        if drop > TM_MATCH_REGRESSION_THRESHOLD_PP:
            regressions.append({
                "league_name": league,
                "baseline_pct": base_pct,
                "current_pct": round(cur_pct, 1),
                "drop_pp": round(drop, 1),
            })

    return {"regressions": sorted(regressions, key=lambda r: -r["drop_pp"])}


def get_remaining_queue() -> list[tuple]:
    entries = []
    with open(QUEUE_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                entries.append((parts[0], parts[1], parts[2]))
    return entries


def format_body(runs: list[dict], remaining: list[tuple], tm_match: dict | None = None) -> str:
    today = date.today().strftime("%Y-%m-%d")
    lines = [f"SofaScore backfill — {today}", "=" * 48, ""]

    if runs:
        n_ok = sum(1 for r in runs if r["success"])
        n_fail = len(runs) - n_ok
        lines.append(f"RUNS TODAY  ({n_ok} OK, {n_fail} failed)\n")
        for r in runs:
            icon = "OK  " if r["success"] else "FAIL"
            lines.append(f"  [{icon}]  {r['slot']:8s}  {r['label']}")
            if r["summary"]:
                lines.append(f"           {r['summary']}")
            if not r["success"] and r["error"]:
                lines.append(f"           ⚠️  {r['error']}")
        lines.append("")
    else:
        lines.append("No runs recorded today (queue may be empty or machine was asleep).\n")

    lines.append(f"QUEUE REMAINING  ({len(remaining)} seasons)\n")
    if remaining:
        days_left = max(1, len(remaining) // 6 + (1 if len(remaining) % 6 else 0))
        for i, (tid, sid, label) in enumerate(remaining[:10]):
            arrow = "→" if i == 0 else " "
            lines.append(f"  {arrow} {label:<42}  (tid={tid} sid={sid})")
        if len(remaining) > 10:
            lines.append(f"    ... and {len(remaining) - 10} more")
        lines.append(f"\n  ~{days_left} day(s) to clear at 6 slots/day")
    else:
        lines.append("  ✅ Queue is empty — backfill complete!")

    if tm_match is not None:
        lines.append("")
        if "error" in tm_match:
            lines.append(f"TM MATCH-QUALITY CHECK  ⚠️  skipped ({tm_match['error']})")
        elif tm_match["regressions"]:
            lines.append(f"TM MATCH-QUALITY CHECK  ⚠️  {len(tm_match['regressions'])} league(s) regressed\n")
            for r in tm_match["regressions"]:
                lines.append(
                    f"  ⚠️  {r['league_name']:<24s}  {r['baseline_pct']}% → {r['current_pct']}%  "
                    f"(-{r['drop_pp']}pp)"
                )
            lines.append(f"\n  Threshold: >{TM_MATCH_REGRESSION_THRESHOLD_PP}pp below baseline. "
                          f"Baseline captured {json.loads(TM_MATCH_BASELINE_FILE.read_text())['_captured_date']}.")
        else:
            lines.append("TM MATCH-QUALITY CHECK  ✅  no league regressed beyond threshold")

    return "\n".join(lines)


def send_email(subject: str, body: str, config: dict) -> None:
    msg = MIMEMultipart()
    msg["From"] = config["GMAIL_USER"]
    msg["To"] = config["TO_EMAIL"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(config["GMAIL_USER"], config["GMAIL_APP_PASSWORD"])
        smtp.send_message(msg)


def main() -> None:
    config = load_config()
    runs = parse_slot_logs()
    remaining = get_remaining_queue()
    tm_match = check_tm_match_quality()

    today = date.today().strftime("%Y-%m-%d")
    n_ok = sum(1 for r in runs if r["success"])
    n_fail = sum(1 for r in runs if not r["success"])

    subject_flags = []
    if n_fail:
        subject_flags.append(f"{n_fail} FAILED")
    if tm_match.get("regressions"):
        subject_flags.append(f"{len(tm_match['regressions'])} TM regression(s)")
    flag_str = f", {', '.join(subject_flags)}" if subject_flags else ""

    if runs:
        subject = f"[RZ] {today} — {n_ok} OK{flag_str} | {len(remaining)} in queue"
    else:
        subject = f"[RZ] {today} — no runs{flag_str} | {len(remaining)} in queue"

    body = format_body(runs, remaining, tm_match)
    send_email(subject, body, config)
    print(f"Sent: {subject}")


if __name__ == "__main__":
    main()
