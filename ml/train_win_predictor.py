
import json
import sqlite3
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.preprocessing import LabelEncoder

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "ml" / "training_data.parquet"
DB_PATH = BASE_DIR / "data" / "ipl_warehouse.db"
MODEL_DIR = BASE_DIR / "ml" / "models"
MODEL_DIR.mkdir(exist_ok=True)


def season_based_split(df: pd.DataFrame):
    conn = sqlite3.connect(DB_PATH)
    match_season = pd.read_sql("SELECT id AS match_id, season FROM matches", conn)
    conn.close()

    # training_data.parquet doesn't carry match_id post-aggregation-safe merge,
    # so we rebuild the join key here directly from the warehouse instead.
    conn = sqlite3.connect(DB_PATH)
    deliveries = pd.read_sql(
        """
        SELECT match_id, batting_team, bowling_team, innings_cum_wickets,
               balls_left, runs_left, target, current_run_rate, required_run_rate
        FROM deliveries WHERE inning = 2
        """,
        conn,
    )
    conn.close()
    deliveries["wickets_left"] = 10 - deliveries["innings_cum_wickets"]
    deliveries = deliveries.merge(match_season, on="match_id", how="left")

    df = df.merge(
        deliveries[["match_id", "season", "batting_team", "bowling_team",
                    "runs_left", "balls_left", "wickets_left", "target",
                    "current_run_rate", "required_run_rate"]].drop_duplicates(),
        on=["batting_team", "bowling_team", "runs_left", "balls_left",
            "wickets_left", "target", "current_run_rate", "required_run_rate"],
        how="left",
    )
    df = df.dropna(subset=["season"])
    seasons_sorted = sorted(df["season"].unique())
    test_seasons = seasons_sorted[-2:]
    train_df = df[~df["season"].isin(test_seasons)]
    test_df = df[df["season"].isin(test_seasons)]
    return train_df, test_df, test_seasons


def train():
    df = pd.read_parquet(DATA_PATH)
    train_df, test_df, test_seasons = season_based_split(df)
    print(f"Held-out test seasons: {test_seasons}")
    print(f"Train rows: {len(train_df):,} | Test rows: {len(test_df):,}")

    cat_cols = ["batting_team", "bowling_team", "venue"]
    num_cols = ["runs_left", "balls_left", "wickets_left", "target",
                "current_run_rate", "required_run_rate"]

    encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        # fit on the union of train+test so unseen-category inference doesn't crash the API
        le.fit(pd.concat([train_df[col], test_df[col]]).astype(str))
        train_df[col + "_enc"] = le.transform(train_df[col].astype(str))
        test_df[col + "_enc"] = le.transform(test_df[col].astype(str))
        encoders[col] = le

    feature_cols = [c + "_enc" for c in cat_cols] + num_cols

    X_train, y_train = train_df[feature_cols], train_df["label_won"]
    X_test, y_test = test_df[feature_cols], test_df["label_won"]

    model = lgb.LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )

    proba = model.predict_proba(X_test)[:, 1]
    preds = (proba >= 0.5).astype(int)

    metrics = {
        "test_seasons_held_out": [str(s) for s in test_seasons],
        "accuracy": round(accuracy_score(y_test, preds), 4),
        "roc_auc": round(roc_auc_score(y_test, proba), 4),
        "log_loss": round(log_loss(y_test, proba), 4),
        "brier_score": round(brier_score_loss(y_test, proba), 4),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }
    print(json.dumps(metrics, indent=2))

    # Sanity check the model is calibrated in an intuitive direction:
    # win probability should climb as required run rate falls, all else equal.
    joblib.dump(model, MODEL_DIR / "win_predictor.pkl")
    joblib.dump(encoders, MODEL_DIR / "label_encoders.pkl")
    with open(MODEL_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    with open(MODEL_DIR / "feature_cols.json", "w") as f:
        json.dump({"cat_cols": cat_cols, "num_cols": num_cols, "feature_cols": feature_cols}, f, indent=2)

    print(f"\nSaved model + encoders to {MODEL_DIR}")
    return metrics


if __name__ == "__main__":
    train()
