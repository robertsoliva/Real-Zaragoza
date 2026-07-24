import os
import json
from flask import Flask, render_template, jsonify, request
from google.cloud import bigquery
import anthropic

app = Flask(__name__)

BQ_PROJECT = os.environ.get("GCP_PROJECT_ID", "real-zaragoza-500608")
bq = bigquery.Client(project=BQ_PROJECT)
claude = anthropic.Anthropic()

POSITION_NEED = {
    "F": 3,   # striker — top priority
    "M": 2,   # creative/box-to-box mid
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
}


def run_query(sql):
    return list(bq.query(sql).result())


def compute_fit_score(p):
    score = 0.0
    breakdown = {}

    # 1. Position need (0–3)
    pos_score = POSITION_NEED.get(p.get("primary_position", ""), 1)
    score += pos_score
    breakdown["position_need"] = pos_score

    # 2. Output quality (0–4): weighted goals+assists per 90 + rating
    g90 = float(p.get("goals_p90") or 0)
    a90 = float(p.get("assists_p90") or 0)
    rating = float(p.get("avg_rating") or 6.5)
    output = min((g90 + a90) * 3 + (rating - 6.0) * 0.5, 4.0)
    score += output
    breakdown["output_quality"] = round(output, 2)

    # 3. League adjustment (0–2)
    league_q = LEAGUE_QUALITY.get(p.get("league_name", ""), 1.2)
    league_score = min((league_q - 1.0) * 2, 2.0)
    score += league_score
    breakdown["league_adjustment"] = round(league_score, 2)

    # 4. Experience (0–1): minutes threshold
    mins = int(p.get("total_minutes") or 0)
    exp = min(mins / 2000, 1.0)
    score += exp
    breakdown["experience"] = round(exp, 2)

    total = round(min(score, 10.0), 1)
    breakdown["total"] = total
    return total, breakdown


def get_narrative(player_row, score, breakdown):
    context = f"""
Real Zaragoza are in 1RFEF (Spanish 3rd division) after relegation. Key needs: striker (top priority), wingers, creative midfielder. Budget is tight — Primera RFEF salary cap applies.

Player being evaluated:
- Name: {player_row['player_name']}
- Position: {player_row['primary_position']}
- Age: {player_row.get('age', 'unknown')}
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


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/squad")
def squad():
    rows = run_query("""
        SELECT name, position, age, nationality, height, market_value_eur,
               jersey_number, player_id
        FROM `real-zaragoza-500608.rz_silver.silver_squad`
        WHERE ingested_date = (SELECT MAX(ingested_date) FROM `real-zaragoza-500608.rz_silver.silver_squad`)
        ORDER BY
          CASE WHEN position LIKE '%Portero%' THEN 1
               WHEN position LIKE '%entral%' OR position LIKE '%efensa%' THEN 2
               WHEN position LIKE '%entro%' OR position LIKE '%Pivote%' OR position LIKE '%Medio%' THEN 3
               ELSE 4 END,
          name
    """)
    players = [dict(r) for r in rows]
    return render_template("squad.html", players=players)


@app.route("/calculator")
def calculator():
    rows = run_query("""
        SELECT DISTINCT player_name, team_name, league_name, season_id,
               primary_position, avg_rating
        FROM `real-zaragoza-500608.rz_gold.gold_player_season`
        WHERE total_minutes >= 450
          AND league_name != '1RFEF'
          AND season_id IN (
            SELECT MAX(season_id)
            FROM `real-zaragoza-500608.rz_gold.gold_player_season`
            WHERE total_minutes >= 450
            GROUP BY league_name
          )
        ORDER BY league_name, player_name
    """)
    players = [dict(r) for r in rows]
    return render_template("calculator.html", players=players)


@app.route("/api/fit", methods=["POST"])
def api_fit():
    data = request.json
    player_name = data.get("player_name")
    season_id = data.get("season_id")
    league_name = data.get("league_name")

    rows = run_query(f"""
        SELECT *
        FROM `real-zaragoza-500608.rz_gold.gold_player_season`
        WHERE player_name = '{player_name.replace("'", "\\'")}'
          AND season_id = '{season_id}'
          AND league_name = '{league_name}'
        LIMIT 1
    """)

    if not rows:
        return jsonify({"error": "Player not found"}), 404

    p = dict(rows[0])
    score, breakdown = compute_fit_score(p)
    narrative = get_narrative(p, score, breakdown)

    return jsonify({
        "player": p,
        "score": score,
        "breakdown": breakdown,
        "narrative": narrative,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5050)
