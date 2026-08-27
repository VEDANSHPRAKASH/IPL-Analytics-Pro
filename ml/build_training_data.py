
import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ipl_warehouse.db"
OUT_PATH = BASE_DIR / "ml" / "training_data.parquet"


def build():
    conn = sqlite3.connect(DB_PATH)

    deliveries = pd.read_sql(
        """
        SELECT match_id, inning, batting_team, bowling_team,
               innings_cum_runs, innings_cum_wickets, balls_left,
               runs_left, target, current_run_rate, required_run_rate
        FROM deliveries
        WHERE inning = 2
        """,
        conn,
    )
    matches = pd.read_sql("SELECT id AS match_id, winner, venue, result FROM matches", conn)
    conn.close()

    df = deliveries.merge(matches, on="match_id", how="inner")

    # Drop no-result / abandoned matches — no clean win/loss label
    df = df[df["result"].notna() & (df["result"] != "NA")]
    df = df.dropna(subset=["runs_left", "required_run_rate", "winner"])

    df["wickets_left"] = 10 - df["innings_cum_wickets"]
    df["label_won"] = (df["batting_team"] == df["winner"]).astype(int)

    # Only keep balls where the chase is still mathematically alive
    df = df[(df["runs_left"] >= 0) & (df["wickets_left"] >= 0) & (df["balls_left"] >= 0)]

    feature_cols = [
        "batting_team", "bowling_team", "venue",
        "runs_left", "balls_left", "wickets_left",
        "target", "current_run_rate", "required_run_rate",
    ]
    final = df[feature_cols + ["label_won"]].reset_index(drop=True)

    final.to_parquet(OUT_PATH, index=False)
    print(f"Training data built: {len(final):,} rows -> {OUT_PATH}")
    print(f"Win-rate balance: {final['label_won'].mean():.3f}")
    return final


if __name__ == "__main__":
    build()
