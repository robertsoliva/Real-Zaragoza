import os
import json
from datetime import date
from decimal import Decimal
from flask import Flask, render_template, jsonify, request
from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
import anthropic

app = Flask(__name__)

BQ_PROJECT = os.environ.get("GCP_PROJECT_ID", "real-zaragoza-500608")
bq = bigquery.Client(project=BQ_PROJECT)
claude = anthropic.Anthropic()

POSITION_NEED = {
    "F": 3,
    "M": 2,
    "D": 1,
    "G": 1,
}

LEAGUE_QUALITY = {
    "LaLiga2": 2.0, "Serie B": 2.0, "Ligue 2": 2.0,
    "J1 League": 1.8, "Turkish Süper Lig": 1.8,
    "Austrian Bundesliga": 1.5, "Norwegian Eliteserien": 1.5,
    "Romanian SuperLiga": 1.4, "Allsvenskan": 1.5,
    "MLS": 1.5, "Korean K League 1": 1.5, "Brasileirao Serie B": 1.5,
    "Mozzart Bet Superliga": 1.2, "Eerste Divisie": 1.6,
    "Moldovan Super Liga": 1.0, "1RFEF": 1.0,
    "Eredivisie": 2.0, "Belgian Pro League": 1.8, "Liga Portugal": 1.8,
    "Bundesliga": 2.5, "2. Bundesliga": 2.0,
    "Premier League": 3.0, "La Liga": 2.5, "Serie A": 2.5, "Ligue 1": 2.5,
}


def run_query(sql, params=None):
    if params:
        job_config = QueryJobConfig(query_parameters=params)
        return list(bq.query(sql, job_config=job_config).result())
    return list(bq.query(sql).result())


def _serialize(v):
    if v is None:
        return None
    if isinstance(v, (date,)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def row_to_dict(row):
    return {k: _serialize(v) for k, v in dict(row).items()}


def compute_fit_score(p):
    score = 0.0
    breakdown = {}

    pos_score = POSITION_NEED.get(p.get("primary_position", ""), 1)
    score += pos_score
    breakdown["position_need"] = pos_score

    g90 = float(p.get("goals_p90") or 0)
    a90 = float(p.get("assists_p90") or 0)
    rating = float(p.get("avg_rating") or 6.5)
    output = min((g90 + a90) * 3 + (rating - 6.0) * 0.5, 4.0)
    score += output
    breakdown["output_quality"] = round(output, 2)

    league_q = LEAGUE_QUALITY.get(p.get("league_name", ""), 1.2)
    league_score = min((league_q - 1.0) * 2, 2.0)
    score += league_score
    breakdown["league_adjustment"] = round(league_score, 2)

    mins = int(p.get("total_minutes") or 0)
    exp = min(mins / 2000, 1.0)
    score += exp
    breakdown["experience"] = round(exp, 2)

    total = round(min(score, 10.0), 1)
    breakdown["total"] = total
    return total, breakdown


def get_narrative(player_row, score, breakdown):
    context = f"""
Real Zaragoza are in 1RFEF (Spanish 3rd division) after relegation. Key needs: striker (top priority), wingers, creative midfielder. Budget is tight — Primera RFEF salary cap applies (~€5-6M total).

Player being evaluated:
- Name: {player_row['player_name']}
- Position: {player_row['primary_position']}
- League: {player_row['league_name']} (season {player_row['season_id']})
- Club: {player_row['team_name']}
- Matches: {player_row['matches']} | Minutes: {player_row['total_minutes']}
- Rating: {player_row['avg_rating']}
- Goals: {player_row['goals']} | Assists: {player_row['assists']}
- Goals/90: {player_row['goals_p90']} | Assists/90: {player_row['assists_p90']}
- Shots/90: {player_row['shots_p90']} | Key passes/90: {player_row['key_passes_p90']}
- Pass accuracy: {player_row['pass_acc_pct']}% | Duel win %: {player_row['duel_win_pct']}%

Fit score: {score}/10 (position need: {breakdown['position_need']}/3, output quality: {breakdown['output_quality']}/4, league adjustment: {breakdown['league_adjustment']}/2, experience: {breakdown['experience']}/1)

Write a 3-sentence scouting verdict for Real Zaragoza. Be direct: does this player fit? What is the key strength and the key risk? End with a clear recommendation (sign / loan / pass).
"""
    msg = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": context}]
    )
    return msg.content[0].text


def compute_financial_fit(p):
    wage_annual = float(p.get("wage_eur_annual") or 0)
    market_value = float(p.get("market_value_eur") or 0)
    contract_expiry_raw = p.get("contract_expiry")
    age = int(p.get("age") or 0)
    wage_source = p.get("wage_source")

    if wage_annual == 0:
        wage_tier = "unknown"
        wage_label = "No wage data"
    elif wage_annual < 100000:
        wage_tier = "very_affordable"
        wage_label = "Very affordable (<€100k/yr)"
    elif wage_annual < 250000:
        wage_tier = "affordable"
        wage_label = "Affordable (€100–250k/yr)"
    elif wage_annual < 500000:
        wage_tier = "costly"
        wage_label = "Costly (€250–500k/yr)"
    else:
        wage_tier = "out_of_budget"
        wage_label = "Out of budget (>€500k/yr)"

    contract_months_remaining = None
    if contract_expiry_raw:
        try:
            if hasattr(contract_expiry_raw, "year"):
                expiry = contract_expiry_raw
            else:
                expiry = date.fromisoformat(str(contract_expiry_raw))
            today = date.today()
            contract_months_remaining = (expiry - today).days / 30
        except Exception:
            pass

    if contract_months_remaining is not None and contract_months_remaining <= 6:
        transfer_route = "free"
        transfer_label = "Free agent or near-free"
    elif contract_months_remaining is not None and contract_months_remaining <= 13:
        transfer_route = "expiring"
        transfer_label = "Expiring contract — low fee"
    elif market_value == 0:
        transfer_route = "unknown"
        transfer_label = "Transfer cost unknown"
    elif market_value < 300000:
        transfer_route = "buy"
        transfer_label = "Affordable buy (<€300k)"
    elif market_value < 1000000:
        transfer_route = "loan_or_buy"
        transfer_label = "Loan or small fee (€300k–1M)"
    elif market_value < 3000000:
        transfer_route = "loan"
        transfer_label = "Loan preferred (€1–3M)"
    else:
        transfer_route = "fee_required"
        transfer_label = "Large fee required (>€3M)"

    if age == 0:
        age_profile = "unknown"
        age_label = "Age unknown"
    elif age <= 20:
        age_profile = "youth"
        age_label = f"Youth (age {age}) — loan target"
    elif age <= 23:
        age_profile = "young"
        age_label = f"Young (age {age}) — developing"
    elif age <= 27:
        age_profile = "prime"
        age_label = f"Prime age ({age})"
    elif age <= 30:
        age_profile = "experienced"
        age_label = f"Experienced (age {age})"
    else:
        age_profile = "veteran"
        age_label = f"Veteran (age {age})"

    good_wage = wage_tier in ("very_affordable", "affordable")
    good_transfer = transfer_route in ("free", "expiring", "buy", "loan_or_buy")
    bad_wage = wage_tier == "out_of_budget"
    bad_transfer = transfer_route == "fee_required"

    if good_wage and good_transfer:
        overall = "green"
        overall_label = "Good financial fit"
    elif bad_wage or bad_transfer:
        overall = "red"
        overall_label = "Difficult financial fit"
    else:
        overall = "amber"
        overall_label = "Moderate financial fit"

    return {
        "wage_tier": wage_tier,
        "wage_label": wage_label,
        "wage_annual": wage_annual,
        "wage_weekly": float(p.get("wage_eur_weekly") or 0),
        "wage_source": wage_source,
        "transfer_route": transfer_route,
        "transfer_label": transfer_label,
        "market_value": market_value,
        "contract_months_remaining": (
            round(contract_months_remaining) if contract_months_remaining is not None else None
        ),
        "age_profile": age_profile,
        "age_label": age_label,
        "age": age,
        "overall": overall,
        "overall_label": overall_label,
    }


def get_scout_narrative(p, bench, fin_fit):
    source_note = "" if fin_fit["wage_source"] == "capology_actual" else " [model estimate]"
    wage_display = (
        f"€{int(fin_fit['wage_annual']):,}/yr{source_note}"
        if fin_fit["wage_annual"] > 0 else "unknown"
    )
    mv_display = f"€{int(fin_fit['market_value']):,}" if fin_fit["market_value"] > 0 else "unknown"

    bench_context = ""
    if bench:
        bench_context = f"""
League avg ({bench.get('league_name')} · {bench.get('primary_position')} · {bench.get('player_count')} players):
Rating {bench.get('avg_rating', '—')} | G/90 {bench.get('avg_goals_p90', '—')} | A/90 {bench.get('avg_assists_p90', '—')} | Shots/90 {bench.get('avg_shots_p90', '—')} | KP/90 {bench.get('avg_key_passes_p90', '—')} | Pass% {bench.get('avg_pass_acc_pct', '—')} | Duel% {bench.get('avg_duel_win_pct', '—')} | Aerial% {bench.get('avg_aerial_win_pct', '—')}"""

    context = f"""You are a football scout writing a report for Real Zaragoza CF.

CLUB CONTEXT: Playing in Primera RFEF (Spanish 3rd tier) 2026-27, targeting immediate promotion back to Segunda División. New majority owner (A.GAIN Capital) backed €20M capital injection. Squad budget ~€5–6M — one of the highest in the category. Key signings already done: Emil Hansson (LW), Edu Espiau (CF), Ander Herrera (MF), Diego González (CB). Remaining gaps: additional attacking depth, left-back cover.

PLAYER PROFILE:
Name: {p.get('player_name')} | Position: {p.get('tm_position') or p.get('sofascore_position')} | Age: {p.get('age', '—')}
Nationality: {p.get('nationality', '—')} | Height: {p.get('height', '—')} | Foot: {p.get('foot', '—')}
Club: {p.get('team_name')} ({p.get('league_name')}, season {p.get('season_id')})
Previous club: {p.get('signed_from') or '—'} | Contract expiry: {p.get('contract_expiry', '—')}

SEASON STATS:
{p.get('matches')} apps / {p.get('total_minutes')} min | Rating: {p.get('avg_rating')}
Goals {p.get('goals')} ({p.get('goals_p90')}/90) | Assists {p.get('assists')} ({p.get('assists_p90')}/90)
Shots/90: {p.get('shots_p90')} | xG/match: {p.get('avg_xg_per_match')} | KP/90: {p.get('key_passes_p90')}
Pass%: {p.get('pass_acc_pct')} | Touches/90: {p.get('touches_p90')}
Tackles/90: {p.get('tackles_p90')} | Int/90: {p.get('interceptions_p90')}
Duel%: {p.get('duel_win_pct')} | Aerial%: {p.get('aerial_win_pct')} | Yellows: {p.get('yellows')}{bench_context}

FINANCIAL:
Market value: {mv_display} | Wage: {wage_display}
Transfer route: {fin_fit['transfer_label']} | Financial fit: {fin_fit['overall_label']}
Age profile: {fin_fit['age_label']}

Write a 5-sentence scouting verdict. Cover in order:
1. Player type — position, style, standout physical/technical attribute
2. Statistical analysis — strengths and weaknesses vs league benchmark
3. Positional fit — does this fill a genuine Zaragoza need for the 1RFEF promotion push?
4. Financial picture — wage realism for 1RFEF budget, transfer route, contract situation
5. Final call: Sign / Loan / Monitor / Pass — one specific reason

Be direct. Use numbers. Flag model-estimated wages if not confirmed real data."""

    msg = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=450,
        messages=[{"role": "user", "content": context}]
    )
    return msg.content[0].text


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/squad")
def squad():
    rows = run_query("""
        SELECT name, position, age, nationality, height, market_value_eur,
               jersey_number, player_id
        FROM `real-zaragoza-500608.silver.rz_squad`
        WHERE ingested_date = (SELECT MAX(ingested_date) FROM `real-zaragoza-500608.silver.rz_squad`)
        ORDER BY
          CASE WHEN position LIKE '%Portero%' THEN 1
               WHEN position LIKE '%entral%' OR position LIKE '%efensa%' THEN 2
               WHEN position LIKE '%entro%' OR position LIKE '%Pivote%' OR position LIKE '%Medio%' THEN 3
               ELSE 4 END,
          name
    """)
    players = [row_to_dict(r) for r in rows]
    return render_template("squad.html", players=players)


@app.route("/calculator")
def calculator():
    rows = run_query("""
        WITH latest AS (
          SELECT league_name, MAX(CAST(season_id AS INT64)) AS max_sid
          FROM `real-zaragoza-500608.gold.fct_player_season_stats`
          WHERE total_minutes >= 450
          GROUP BY league_name
        )
        SELECT DISTINCT s.player_name, s.team_name, s.league_name,
               s.season_id, s.primary_position, s.avg_rating
        FROM `real-zaragoza-500608.gold.fct_player_season_stats` s
        JOIN latest l ON s.league_name = l.league_name
          AND CAST(s.season_id AS INT64) = l.max_sid
        WHERE s.total_minutes >= 450
          AND s.league_name != '1RFEF'
        ORDER BY s.league_name, s.player_name
    """)
    players = [row_to_dict(r) for r in rows]
    return render_template("calculator.html", players=players)


@app.route("/scouting")
def scouting():
    rows = run_query("""
        WITH latest AS (
          SELECT league_name, MAX(CAST(season_id AS INT64)) AS max_sid
          FROM `real-zaragoza-500608.gold.agg_scouting_player_season`
          WHERE total_minutes >= 450
          GROUP BY league_name
        )
        SELECT s.player_name, s.team_name, s.league_name, s.season_id,
               COALESCE(s.tm_position, s.sofascore_position) AS position,
               s.sofascore_position,
               s.avg_rating, s.age, s.nationality, s.market_value_eur
        FROM `real-zaragoza-500608.gold.agg_scouting_player_season` s
        JOIN latest l ON s.league_name = l.league_name
          AND CAST(s.season_id AS INT64) = l.max_sid
        WHERE s.total_minutes >= 450
        ORDER BY s.league_name, s.player_name
    """)
    players = [row_to_dict(r) for r in rows]
    return render_template("scouting.html", players=players)


@app.route("/api/fit", methods=["POST"])
def api_fit():
    data = request.json
    player_name = data.get("player_name")
    season_id = data.get("season_id")
    league_name = data.get("league_name")

    rows = run_query(
        """
        SELECT *
        FROM `real-zaragoza-500608.gold.fct_player_season_stats`
        WHERE player_name = @player_name
          AND season_id = @season_id
          AND league_name = @league_name
        LIMIT 1
        """,
        params=[
            ScalarQueryParameter("player_name", "STRING", player_name),
            ScalarQueryParameter("season_id", "STRING", str(season_id)),
            ScalarQueryParameter("league_name", "STRING", league_name),
        ],
    )

    if not rows:
        return jsonify({"error": "Player not found"}), 404

    p = row_to_dict(rows[0])
    score, breakdown = compute_fit_score(p)
    narrative = get_narrative(p, score, breakdown)

    return jsonify({"player": p, "score": score, "breakdown": breakdown, "narrative": narrative})


@app.route("/api/scout", methods=["POST"])
def api_scout():
    data = request.json
    player_name = data.get("player_name")
    season_id = data.get("season_id")
    league_name = data.get("league_name")

    params = [
        ScalarQueryParameter("player_name", "STRING", player_name),
        ScalarQueryParameter("season_id", "STRING", str(season_id)),
        ScalarQueryParameter("league_name", "STRING", league_name),
    ]

    rows = run_query(
        """
        SELECT *
        FROM `real-zaragoza-500608.gold.agg_scouting_player_season`
        WHERE player_name = @player_name
          AND season_id = @season_id
          AND league_name = @league_name
        LIMIT 1
        """,
        params=params,
    )

    if not rows:
        return jsonify({"error": "Player not found"}), 404

    p = row_to_dict(rows[0])

    bench_rows = run_query(
        """
        SELECT *
        FROM `real-zaragoza-500608.gold.agg_league_player_benchmarks`
        WHERE league_name = @league_name
          AND season_id = @season_id
          AND primary_position = @pos
        LIMIT 1
        """,
        params=[
            ScalarQueryParameter("league_name", "STRING", league_name),
            ScalarQueryParameter("season_id", "STRING", str(season_id)),
            ScalarQueryParameter("pos", "STRING", p.get("sofascore_position", "M")),
        ],
    )
    bench = row_to_dict(bench_rows[0]) if bench_rows else {}

    fin_fit = compute_financial_fit(p)
    narrative = get_scout_narrative(p, bench, fin_fit)

    return jsonify({"player": p, "benchmarks": bench, "financial_fit": fin_fit, "narrative": narrative})


if __name__ == "__main__":
    app.run(debug=True, port=5050)
