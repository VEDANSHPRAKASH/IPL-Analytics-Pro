
import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "data" / "ipl_warehouse.db"

# ---------------------------------------------------------------------------
# 1. Team-name normalization map (handles franchise renames/relocations)
# ---------------------------------------------------------------------------
TEAM_NAME_MAP = {
    "Delhi Daredevils": "Delhi Capitals",              # rebrand, 2019 — same franchise
    "Kings XI Punjab": "Punjab Kings",                  # rebrand, 2021 — same franchise
    "Rising Pune Supergiant": "Rising Pune Supergiants",  # spelling variant across seasons
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",  # rebrand, 2024 — same franchise
    # NOTE: "Deccan Chargers" is deliberately NOT mapped to "Sunrisers Hyderabad".
    # Deccan Chargers was terminated by the BCCI in 2012; SRH is a distinct
    # franchise awarded in 2013 under different ownership. Merging them would
    # be a factual error, even though they share a home city/stadium.
    # Likewise "Pune Warriors India" and "Rising Pune Supergiant(s)" are left
    # as separate franchises — different ownership groups, non-consecutive seasons.
}


def normalize_team(name: str) -> str:
    if pd.isna(name):
        return name
    return TEAM_NAME_MAP.get(name, name)


def phase_of_over(over: int) -> str:
    """Powerplay = overs 0-5, Middle = 6-14, Death = 15-19 (0-indexed overs)."""
    if over <= 5:
        return "Powerplay"
    elif over <= 14:
        return "Middle"
    else:
        return "Death"


def build():
    print("Reading raw CSVs...")
    matches = pd.read_csv(DATA_DIR / "matches.csv")
    deliveries = pd.read_csv(DATA_DIR / "deliveries.csv")

    print(f"  matches: {len(matches):,} rows | deliveries: {len(deliveries):,} rows")

    # -----------------------------------------------------------------
    # 2. Clean & normalize `matches`
    # -----------------------------------------------------------------
    for col in ["team1", "team2", "toss_winner", "winner"]:
        matches[col] = matches[col].apply(normalize_team)

    matches["date"] = pd.to_datetime(matches["date"], errors="coerce")
    matches["season"] = matches["season"].astype(str)
    matches["win_by_wickets"] = matches.apply(
        lambda r: r["result_margin"] if r["result"] == "wickets" else 0, axis=1
    )
    matches["win_by_runs"] = matches.apply(
        lambda r: r["result_margin"] if r["result"] == "runs" else 0, axis=1
    )
    # Convenience flag: did the toss-winner also win the match?
    matches["toss_win_match_win"] = (matches["toss_winner"] == matches["winner"]).astype(int)

    # -----------------------------------------------------------------
    # 3. Clean & normalize `deliveries`, engineer match-state columns
    # -----------------------------------------------------------------
    deliveries["batting_team"] = deliveries["batting_team"].apply(normalize_team)
    deliveries["bowling_team"] = deliveries["bowling_team"].apply(normalize_team)
    deliveries["phase"] = deliveries["over"].apply(phase_of_over)
    deliveries["is_boundary"] = deliveries["batsman_runs"].isin([4, 6]).astype(int)
    deliveries["is_dot"] = (deliveries["total_runs"] == 0).astype(int)

    # Legal delivery = not a wide and not a no-ball (used for strike-rate/over-count math)
    deliveries["is_legal_delivery"] = (~deliveries["extras_type"].isin(["wides", "noballs"])).astype(int)

    # -----------------------------------------------------------------
    # 4. Engineer ball-by-ball MATCH STATE (for the win-probability model)
    #    cumulative runs, wickets, balls bowled -> current score, target,
    #    required run rate, at every ball of 2nd innings.
    # -----------------------------------------------------------------
    print("Engineering match-state features for win-probability modelling...")
    deliveries.sort_values(["match_id", "inning", "over", "ball"], inplace=True)

    deliveries["innings_cum_runs"] = deliveries.groupby(["match_id", "inning"])["total_runs"].cumsum()
    deliveries["innings_cum_wickets"] = deliveries.groupby(["match_id", "inning"])["is_wicket"].cumsum()
    deliveries["legal_ball_count"] = deliveries.groupby(["match_id", "inning"])["is_legal_delivery"].cumsum()
    deliveries["balls_bowled"] = deliveries["legal_ball_count"]
    deliveries["balls_left"] = (120 - deliveries["balls_bowled"]).clip(lower=0)
    deliveries["current_run_rate"] = (
        deliveries["innings_cum_runs"] / (deliveries["balls_bowled"].replace(0, 1) / 6)
    ).round(2)

    # Innings-1 total (target for innings-2) mapped onto every ball of that match
    first_innings_totals = (
        deliveries[deliveries["inning"] == 1]
        .groupby("match_id")["innings_cum_runs"]
        .max()
        .rename("first_innings_total")
    )
    deliveries = deliveries.merge(first_innings_totals, on="match_id", how="left")
    deliveries["target"] = deliveries["first_innings_total"] + 1
    deliveries["runs_left"] = (deliveries["target"] - deliveries["innings_cum_runs"]).where(
        deliveries["inning"] == 2
    )
    deliveries["required_run_rate"] = (
        deliveries["runs_left"] / (deliveries["balls_left"].replace(0, 1) / 6)
    ).round(2)

    # -----------------------------------------------------------------
    # 5. Write to SQLite warehouse
    # -----------------------------------------------------------------
    print(f"Writing warehouse to {DB_PATH} ...")
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    matches.to_sql("matches", conn, index=False)
    deliveries.to_sql("deliveries", conn, index=False)

    # Dimension tables — makes JOIN-heavy SQL portfolio queries possible
    teams = pd.DataFrame({"team_name": sorted(set(matches["team1"]) | set(matches["team2"]))})
    teams.to_sql("dim_teams", conn, index=False)

    players = pd.DataFrame(
        {"player_name": sorted(set(deliveries["batter"]) | set(deliveries["bowler"]))}
    )
    players.to_sql("dim_players", conn, index=False)

    venues = matches[["venue", "city"]].drop_duplicates().reset_index(drop=True)
    venues.to_sql("dim_venues", conn, index=False)

    # Helpful indexes for the API's live query paths
    cur = conn.cursor()
    cur.execute("CREATE INDEX idx_deliveries_match ON deliveries(match_id)")
    cur.execute("CREATE INDEX idx_deliveries_batter ON deliveries(batter)")
    cur.execute("CREATE INDEX idx_deliveries_bowler ON deliveries(bowler)")
    cur.execute("CREATE INDEX idx_matches_season ON matches(season)")
    conn.commit()
    conn.close()

    print("Warehouse build complete.")
    print(f"  Tables: matches, deliveries, dim_teams, dim_players, dim_venues")


if __name__ == "__main__":
    build()
