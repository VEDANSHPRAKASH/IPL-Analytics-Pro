
import sqlite3
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ipl_warehouse.db"
MODEL_DIR = BASE_DIR / "ml" / "models"

app = FastAPI(
    title="IPL Analytics Pro API",
    description="Ball-by-ball IPL analytics + live win-probability prediction",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the deployed frontend origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Load the trained model + encoders once at startup, not per-request -----
# Broad except is deliberate here: if this were narrowed to FileNotFoundError
# only, any other load failure (e.g. lightgbm not installed so the pickle
# can't be unpickled, a corrupted file, a permissions error) would raise
# uncaught at import time and crash the ENTIRE FastAPI app before it ever
# starts listening — which looks identical to "server not running" from the
# browser's side, and is far harder to diagnose than a printed warning.
try:
    model = joblib.load(MODEL_DIR / "win_predictor.pkl")
    encoders = joblib.load(MODEL_DIR / "label_encoders.pkl")
    MODEL_LOADED = True
except Exception as e:
    MODEL_LOADED = False
    print(f"[WARNING] Win-probability model not loaded: {type(e).__name__}: {e}")
    print("  -> The rest of the API (analytics endpoints) will still work.")
    print("  -> Run: python ml/build_training_data.py && python ml/train_win_predictor.py")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = get_conn()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


# =============================================================================
# Analytics endpoints
# =============================================================================

@app.get("/")
def root():
    return {"status": "ok", "service": "IPL Analytics Pro API"}


@app.get("/api/health")
def health():
    warehouse_exists = DB_PATH.exists()
    return {
        "status": "ok",
        "warehouse_db_found": warehouse_exists,
        "warehouse_path": str(DB_PATH),
        "win_probability_model_loaded": MODEL_LOADED,
    }


@app.get("/api/teams")
def list_teams():
    df = query_df("SELECT team_name FROM dim_teams ORDER BY team_name")
    return df["team_name"].tolist()


@app.get("/api/teams/leaderboard")
def team_leaderboard():
    """Win % leaderboard — same logic as sql/advanced_analytics.sql Q2."""
    sql = """
        WITH team_matches AS (
            SELECT team1 AS team FROM matches
            UNION ALL
            SELECT team2 AS team FROM matches
        ),
        played AS (SELECT team, COUNT(*) AS matches_played FROM team_matches GROUP BY team),
        won AS (
            SELECT winner AS team, COUNT(*) AS matches_won FROM matches
            WHERE winner IS NOT NULL AND winner != 'NA' GROUP BY winner
        )
        SELECT p.team, p.matches_played, COALESCE(w.matches_won, 0) AS matches_won,
               ROUND(100.0 * COALESCE(w.matches_won, 0) / p.matches_played, 2) AS win_pct
        FROM played p LEFT JOIN won w ON p.team = w.team
        WHERE p.matches_played >= 10
        ORDER BY win_pct DESC
    """
    return query_df(sql).to_dict(orient="records")


@app.get("/api/players/top-scorers")
def top_scorers(limit: int = Query(10, le=50)):
    sql = """
        SELECT batter,
               SUM(batsman_runs) AS career_runs,
               COUNT(DISTINCT match_id) AS innings_played,
               ROUND(100.0 * SUM(batsman_runs) / NULLIF(SUM(is_legal_delivery), 0), 2) AS strike_rate
        FROM deliveries
        GROUP BY batter
        ORDER BY career_runs DESC
        LIMIT ?
    """
    return query_df(sql, (limit,)).to_dict(orient="records")


@app.get("/api/players/top-wicket-takers")
def top_wicket_takers(limit: int = Query(10, le=50)):
    sql = """
        SELECT bowler,
               SUM(is_wicket) AS wickets,
               ROUND(6.0 * SUM(total_runs) / NULLIF(SUM(is_legal_delivery), 0), 2) AS economy_rate
        FROM deliveries
        WHERE dismissal_kind NOT IN ('run out', 'retired hurt', 'obstructing the field')
        GROUP BY bowler
        ORDER BY wickets DESC
        LIMIT ?
    """
    return query_df(sql, (limit,)).to_dict(orient="records")


@app.get("/api/venues")
def venue_analytics():
    sql = """
        WITH first_innings_scores AS (
            SELECT match_id, MAX(innings_cum_runs) AS final_score
            FROM deliveries WHERE inning = 1 GROUP BY match_id
        )
        SELECT m.venue, COUNT(*) AS matches_hosted,
               ROUND(AVG(f.final_score), 1) AS avg_first_innings_score
        FROM matches m
        JOIN first_innings_scores f ON m.id = f.match_id
        GROUP BY m.venue
        HAVING COUNT(*) >= 5
        ORDER BY avg_first_innings_score DESC
    """
    return query_df(sql).to_dict(orient="records")


@app.get("/api/head-to-head")
def head_to_head(team1: str, team2: str):
    sql = """
        SELECT team1, team2, winner, date, venue, result, win_by_runs, win_by_wickets
        FROM matches
        WHERE (team1 = ? AND team2 = ?) OR (team1 = ? AND team2 = ?)
        ORDER BY date DESC
    """
    df = query_df(sql, (team1, team2, team2, team1))
    if df.empty:
        raise HTTPException(404, "No matches found between these teams")
    summary = {
        "matches_played": len(df),
        f"{team1}_wins": int((df["winner"] == team1).sum()),
        f"{team2}_wins": int((df["winner"] == team2).sum()),
        "matches": df.to_dict(orient="records"),
    }
    return summary


@app.get("/api/season-champions")
def season_champions():
    sql = """
        WITH final_matches AS (
            SELECT season, MAX(date) AS final_date FROM matches GROUP BY season
        )
        SELECT m.season, m.winner AS champion, m.venue
        FROM matches m
        JOIN final_matches f ON m.season = f.season AND m.date = f.final_date
        ORDER BY m.season
    """
    return query_df(sql).to_dict(orient="records")


# =============================================================================
# Win-probability prediction endpoint
# =============================================================================

class WinProbabilityRequest(BaseModel):
    batting_team: str
    bowling_team: str
    venue: str
    runs_left: int = Field(..., ge=0)
    balls_left: int = Field(..., ge=0, le=120)
    wickets_left: int = Field(..., ge=0, le=10)
    target: int = Field(..., ge=1)


def safe_encode(encoder, value: str) -> int:
    """Falls back to the most frequent training class for an unseen category
    instead of crashing the request — a venue not in training data shouldn't
    500 the API."""
    classes = list(encoder.classes_)
    if value in classes:
        return int(encoder.transform([value])[0])
    return int(encoder.transform([classes[0]])[0])


@app.post("/api/predict-win-probability")
def predict_win_probability(req: WinProbabilityRequest):
    if not MODEL_LOADED:
        raise HTTPException(503, "Model not loaded. Run ml/train_win_predictor.py first.")

    balls_bowled = 120 - req.balls_left
    current_run_rate = (req.target - 1 - req.runs_left) / (balls_bowled / 6) if balls_bowled > 0 else 0.0
    required_run_rate = req.runs_left / (req.balls_left / 6) if req.balls_left > 0 else 99.0

    row = {
        "batting_team_enc": safe_encode(encoders["batting_team"], req.batting_team),
        "bowling_team_enc": safe_encode(encoders["bowling_team"], req.bowling_team),
        "venue_enc": safe_encode(encoders["venue"], req.venue),
        "runs_left": req.runs_left,
        "balls_left": req.balls_left,
        "wickets_left": req.wickets_left,
        "target": req.target,
        "current_run_rate": round(current_run_rate, 2),
        "required_run_rate": round(required_run_rate, 2),
    }
    X = pd.DataFrame([row])
    proba = model.predict_proba(X)[0, 1]

    return {
        "batting_team": req.batting_team,
        "bowling_team": req.bowling_team,
        "batting_team_win_probability": round(float(proba), 4),
        "bowling_team_win_probability": round(float(1 - proba), 4),
        "current_run_rate": round(current_run_rate, 2),
        "required_run_rate": round(required_run_rate, 2),
    }


@app.get("/api/model-info")
def model_info():
    if not MODEL_LOADED:
        raise HTTPException(503, "Model not loaded.")
    import json
    with open(MODEL_DIR / "metrics.json") as f:
        metrics = json.load(f)
    return {
        "model": "LightGBM Classifier",
        "task": "2nd-innings live win probability",
        "evaluation_method": "season-based holdout (not random split, to avoid intra-match leakage)",
        "metrics": metrics,
    }
