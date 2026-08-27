# IPL Analytics Pro

Ball-by-ball analytics and live win-probability prediction for 19 seasons of
IPL cricket (2008–2026) — 1,243 matches, 295,732+ deliveries, built from
[Cricsheet's](https://cricsheet.org) authoritative ball-by-ball archive.

This started as a rebuild of a SQL-only "top teams and players" project into
something closer to how a real sports-analytics team would build it: a
normalized data warehouse, a feature-engineered ML model with an honest
evaluation methodology, an API layer, and a dashboard on top.

---

### Data source

Raw match data is sourced from [Cricsheet](https://cricsheet.org), the
open ball-by-ball archive for professional cricket, via
`cricsheet.org/downloads/ipl_json.zip`. `etl/convert_cricsheet.py` (kept
alongside the pipeline for reproducibility) flattens Cricsheet's per-match
JSON files into the `matches.csv`/`deliveries.csv` schema this project
expects. The conversion was validated by cross-checking every field
against the previous dataset's 1,095 overlapping matches — zero
mismatches across team names, results, margins, and all 260,920
pre-2025 delivery rows.

## Architecture

```
Raw CSVs (matches.csv, deliveries.csv)
        │
        ▼
ETL — etl/build_warehouse.py
  • team-name normalization (true rebrands only)
  • phase-of-play tagging (Powerplay / Middle / Death)
  • ball-by-ball match-state feature engineering
        │
        ▼
SQLite Warehouse — data/ipl_warehouse.db
  matches · deliveries · dim_teams · dim_players · dim_venues
        │
        ├──────────────────────────────┐
        ▼                              ▼
Advanced SQL                    ML Pipeline — ml/
sql/advanced_analytics.sql        build_training_data.py
  window functions, CTEs,          train_win_predictor.py
  ranking, trailing averages       → LightGBM classifier
                                    → season-holdout evaluation
                                          │
                                          ▼
                              FastAPI Backend — api/main.py
                                /api/teams/leaderboard
                                /api/players/top-scorers
                                /api/venues
                                /api/predict-win-probability
                                          │
                                          ▼
                              React Dashboard — frontend/
                                Vite + React 19 + Recharts
                                team/player leaderboards,
                                venue chart, live win-probability
                                simulator
```

**Why this shape, not just SQL scripts:** the original project loaded raw
CSVs straight into a database and ran aggregate queries against them. That
breaks the moment a franchise renames (Delhi Daredevils → Delhi Capitals) or
you need per-ball state (score, wickets, required run rate) that doesn't
exist as a column anywhere in the raw data. Normalizing once in the ETL step
means every query and the ML model downstream can trust the same clean
tables instead of re-deriving fixes ad hoc.

---

## What's in each layer

### 1. ETL (`etl/build_warehouse.py`)
- Normalizes franchise names across relocations/rebrands — **but only true
  renames** (Delhi Daredevils→Capitals, Kings XI Punjab→Punjab Kings,
  RCB→RCB Bengaluru). Deccan Chargers is deliberately kept separate from
  Sunrisers Hyderabad, since SRH is a different franchise awarded in 2013
  after the BCCI terminated Deccan Chargers — merging them would misattribute
  a title.
- Tags every delivery with its phase of play (Powerplay/Middle/Death).
- Engineers ball-by-ball match state: cumulative score, wickets, balls left,
  current run rate, target, required run rate — the feature set the ML
  model trains on.

### 2. Advanced SQL (`sql/advanced_analytics.sql`)
10 queries using window functions (`RANK() OVER`, `AVG() OVER ... ROWS
BETWEEN`), CTEs, and multi-way joins — season champions, team win%
rankings, phase-wise bowler economy, head-to-head records, trailing
3-season form, venue batting-friendliness, closest finishes. All validated
to execute against the real warehouse.

### 3. ML: Live Win-Probability Model (`ml/`)
A LightGBM classifier that predicts a chasing team's win probability from
any point in the 2nd innings (runs needed, balls left, wickets in hand,
required run rate, teams, venue) — the same category of model TV
broadcasts show live.

**Evaluation methodology matters here.** A random train/test split would
leak information: consecutive balls from the same chase are highly
correlated, so a model can "memorize" a match's outcome from a nearby row
and report inflated accuracy. This model is instead evaluated on a
**season-based holdout** — trained on 2008–2024, tested only on the
unseen 2025–2026 seasons:

| Metric | Value |
|---|---|
| Accuracy | 78.0% |
| ROC-AUC | 0.902 |
| Log loss | 0.442 |
| Brier score | 0.145 |

### 4. API (`api/main.py`)
FastAPI service exposing the warehouse analytics and the model as REST
endpoints, with CORS enabled for the dashboard and graceful fallback for
unseen categorical values (a venue not in training data doesn't 500 the
request).

### 5. Dashboard (`frontend/`)
Vite + React 19 + Recharts. Three views: team/venue overview, player
leaderboards, and a live win-probability simulator that calls the model
in real time.

---

## Running it locally

```bash
# 1. Backend
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt

# (Optional) Rebuild matches.csv/deliveries.csv from raw Cricsheet data —
# only needed if you want to refresh with a newer season. Skip this if
# data/matches.csv and data/deliveries.csv are already present.
# python etl/convert_cricsheet.py <path-to-unzipped-ipl_json.zip> data/

python etl/build_warehouse.py          # builds data/ipl_warehouse.db
python ml/build_training_data.py       # builds ml/training_data.parquet
python ml/train_win_predictor.py       # trains + saves ml/models/win_predictor.pkl

uvicorn api.main:app --reload --port 8000

# 2. Frontend (in a second terminal)
cd frontend
npm install
npm run dev                            # http://localhost:5173
```

The frontend calls the API directly at `http://127.0.0.1:8000/api` by
default (`frontend/src/api/client.js`) — both processes must be running,
and this works the same whether you use `npm run dev` or `npm run build`
+ `npm run preview`. To point at a different backend URL (e.g. a deployed
API), copy `frontend/.env.example` to `frontend/.env` and set
`VITE_API_BASE`.

### Troubleshooting: "Could not reach the API"

This means the browser couldn't reach FastAPI at all — check in this order:

1. **Is uvicorn actually running?** Look at the terminal you started it in.
   If it's not there, `npm run dev`/`preview` alone won't start it — it's a
   separate process that must be running at the same time.
2. **Did you run it from the project root?** `uvicorn api.main:app --reload
   --port 8000` must be run from `ipl-analytics-pro/`, not from inside
   `api/` — otherwise it can't find the `api.main` module.
3. **Did the warehouse/model get built first?** `uvicorn` will start even
   if `data/ipl_warehouse.db` or `ml/models/win_predictor.pkl` don't exist
   yet, but every request will 500. Run the three build steps first:
   `python etl/build_warehouse.py`, `python ml/build_training_data.py`,
   `python ml/train_win_predictor.py`.
4. **Is port 8000 already taken?** Run uvicorn on another port
   (`--port 8001`) and update `VITE_API_BASE` to match.
5. **Missing dependencies?** If `pip install -r requirements.txt` didn't
   fully succeed (e.g. lightgbm failed to build), uvicorn will crash
   silently on import — check the terminal output for a traceback.

---

## Project structure

```
ipl-analytics-pro/
├── data/
│   ├── matches.csv, deliveries.csv       # raw source data
│   └── ipl_warehouse.db                  # built by ETL (not committed)
├── etl/
│   ├── convert_cricsheet.py
│   └── build_warehouse.py
├── sql/
│   └── advanced_analytics.sql
├── ml/
│   ├── build_training_data.py
│   ├── train_win_predictor.py
│   └── models/                           # win_predictor.pkl, metrics.json
├── api/
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api/client.js
│   │   └── components/
│   └── package.json
├── docs/
│   └── resume_bullets.md
└── requirements.txt
```

---

## Talking points for interviews

- **Data normalization decision-making**: explain *why* Deccan Chargers ≠
  Sunrisers Hyderabad but Delhi Daredevils = Delhi Capitals — shows you
  understand the domain, not just the code.
- **Evaluation methodology**: be ready to explain why a season-based
  holdout was used instead of a random split, and what would have gone
  wrong with a random split (data leakage between correlated rows of the
  same match).
- **Feature engineering from event-level data**: ball-by-ball rows had to
  be turned into running match-state features (cumulative sums, target
  computed from the other innings) — this is the same kind of engineering
  used in real-time sports analytics and fraud-detection style systems.
- **Full-stack integration**: SQL warehouse → Python ML → FastAPI → React,
  the same pattern as your other full-stack projects (EMS Pro, SpendSmart).
