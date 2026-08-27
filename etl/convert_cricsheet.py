
import csv
import json
import sys
from pathlib import Path


def convert_match(match_id: int, d: dict):
    info = d["info"]
    outcome = info.get("outcome", {})

    # --- result / winner / super_over -------------------------------------
    if "result" in outcome and outcome["result"] in ("tie", "no result"):
        result = outcome["result"]
        result_margin = None
        if result == "tie":
            winner = outcome.get("eliminator")
        else:
            winner = None
    else:
        winner = outcome.get("winner")
        by = outcome.get("by", {})
        if "runs" in by:
            result, result_margin = "runs", by["runs"]
        elif "wickets" in by:
            result, result_margin = "wickets", by["wickets"]
        else:
            result, result_margin = None, None

    # A super over adds extra innings entries (3rd/4th, occasionally 5th/6th
    # for a repeated tie) beyond the normal two-innings match.
    super_over = "Y" if len(d.get("innings", [])) > 2 else "N"

    # --- target (chasing team's innings carries a `target` block) ---------
    target_runs, target_overs = None, None
    for inn in d.get("innings", []):
        if inn.get("target"):
            target_runs = inn["target"].get("runs")
            target_overs = inn["target"].get("overs")
            break

    umpires = info.get("officials", {}).get("umpires", [])
    teams = info.get("teams", [None, None])

    match_row = {
        "id": match_id,
        "season": str(info.get("season")),
        "city": info.get("city"),
        "date": info.get("dates", [None])[0],
        "match_type": info.get("event", {}).get("stage", "League"),
        "player_of_match": (info.get("player_of_match") or [None])[0],
        "venue": info.get("venue"),
        "team1": teams[0],
        "team2": teams[1],
        "toss_winner": info.get("toss", {}).get("winner"),
        "toss_decision": info.get("toss", {}).get("decision"),
        "winner": winner,
        "result": result,
        "result_margin": result_margin,
        "target_runs": target_runs,
        "target_overs": target_overs,
        "super_over": super_over,
        "method": outcome.get("method"),
        "umpire1": umpires[0] if len(umpires) > 0 else None,
        "umpire2": umpires[1] if len(umpires) > 1 else None,
    }

    # --- deliveries ---------------------------------------------------------
    delivery_rows = []
    for inning_num, inn in enumerate(d.get("innings", []), start=1):
        batting_team = inn.get("team")
        bowling_team = next((t for t in teams if t != batting_team), None)

        for over_block in inn.get("overs", []):
            over_num = over_block["over"]
            for ball_entry in over_block.get("deliveries", []):
                # "actual_delivery" is "over.ball_within_over", counting
                # every delivery bowled including wides/no-balls, which
                # matches the original dataset's `ball` numbering exactly.
                actual = ball_entry.get("actual_delivery")
                if actual is not None:
                    ball_num = int(str(actual).split(".")[1])
                else:
                    ball_num = None

                runs = ball_entry.get("runs", {})
                extras = ball_entry.get("extras", {})
                extras_type = next(iter(extras.keys()), None) if extras else None

                wickets = ball_entry.get("wickets", [])
                is_wicket = 1 if wickets else 0
                player_dismissed = wickets[0].get("player_out") if wickets else None
                dismissal_kind = wickets[0].get("kind") if wickets else None
                fielders = wickets[0].get("fielders", []) if wickets else []
                fielder = fielders[0].get("name") if fielders else None

                delivery_rows.append({
                    "match_id": match_id,
                    "inning": inning_num,
                    "batting_team": batting_team,
                    "bowling_team": bowling_team,
                    "over": over_num,
                    "ball": ball_num,
                    "batter": ball_entry.get("batter"),
                    "bowler": ball_entry.get("bowler"),
                    "non_striker": ball_entry.get("non_striker"),
                    "batsman_runs": runs.get("batter", 0),
                    "extra_runs": runs.get("extras", 0),
                    "total_runs": runs.get("total", 0),
                    "extras_type": extras_type,
                    "is_wicket": is_wicket,
                    "player_dismissed": player_dismissed,
                    "dismissal_kind": dismissal_kind,
                    "fielder": fielder,
                })

    return match_row, delivery_rows


def main():
    json_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    match_cols = ["id", "season", "city", "date", "match_type", "player_of_match",
                  "venue", "team1", "team2", "toss_winner", "toss_decision", "winner",
                  "result", "result_margin", "target_runs", "target_overs",
                  "super_over", "method", "umpire1", "umpire2"]
    delivery_cols = ["match_id", "inning", "batting_team", "bowling_team", "over", "ball",
                      "batter", "bowler", "non_striker", "batsman_runs", "extra_runs",
                      "total_runs", "extras_type", "is_wicket", "player_dismissed",
                      "dismissal_kind", "fielder"]

    json_files = sorted(json_dir.glob("*.json"))
    print(f"Converting {len(json_files)} match files...")

    n_matches, n_deliveries, n_errors = 0, 0, 0

    with open(out_dir / "matches.csv", "w", newline="", encoding="utf-8") as mf, \
         open(out_dir / "deliveries.csv", "w", newline="", encoding="utf-8") as df:

        match_writer = csv.DictWriter(mf, fieldnames=match_cols)
        match_writer.writeheader()
        delivery_writer = csv.DictWriter(df, fieldnames=delivery_cols)
        delivery_writer.writeheader()

        for jf in json_files:
            try:
                match_id = int(jf.stem)
                with open(jf) as f:
                    d = json.load(f)
                match_row, delivery_rows = convert_match(match_id, d)
                match_writer.writerow(match_row)
                delivery_writer.writerows(delivery_rows)
                n_matches += 1
                n_deliveries += len(delivery_rows)
            except Exception as e:
                n_errors += 1
                print(f"  [ERROR] {jf.name}: {type(e).__name__}: {e}")

    print(f"Done. {n_matches} matches, {n_deliveries:,} deliveries, {n_errors} errors.")
    print(f"Output: {out_dir}/matches.csv, {out_dir}/deliveries.csv")


if __name__ == "__main__":
    main()
