# Resume bullets — IPL Analytics Pro

Pick 2–3 depending on the role (Data Analyst vs. ML Engineer framing below).
All numbers here are real, pulled directly from this dataset and this
model's actual evaluation output — nothing here is a placeholder.

## Data Analyst framing

- Built a normalized SQLite data warehouse from 295,732+ ball-by-ball
  records and 1,243 matches spanning 19 IPL seasons (2008–2026), writing an ETL
  pipeline to resolve franchise rebrands/relocations and engineer
  phase-of-play (powerplay/middle/death overs) features.
- Authored 10+ advanced SQL analytics queries using window functions
  (RANK, moving averages via ROWS BETWEEN) and CTEs to surface team
  win-rate rankings, phase-wise bowler economy, and venue scoring
  environments.
- Designed a REST API (FastAPI) serving pre-aggregated analytics to a
  React + Recharts dashboard, replacing static Tableau exports with a
  live, queryable interface.

## ML / Data Science framing

- Engineered a ball-by-ball match-state feature set (runs needed, balls
  remaining, wickets in hand, required run rate) from raw event data and
  trained a LightGBM classifier to predict live 2nd-innings win
  probability, achieving 78.0% accuracy and 0.902 ROC-AUC.
- Evaluated the model on a season-based holdout (trained through 2024,
  tested on unseen 2025–2026 seasons) instead of a random split, to avoid
  data leakage from within-match row correlation — a methodology choice
  I can defend in detail if asked.
- Deployed the trained model behind a FastAPI endpoint with graceful
  handling of unseen categorical values (teams/venues not present in
  training data), and built an interactive React simulator to query it
  in real time.

## One-liner (for a projects list / LinkedIn)

IPL Analytics Pro — SQL + ML dashboard analyzing 19 seasons of IPL
cricket; built a normalized data warehouse, advanced SQL analytics, and a
LightGBM live win-probability model (78.0% accuracy on a season-holdout
test set), served via FastAPI + React.

## Anticipated interview questions (and where to point)

- "Why season-holdout instead of random/k-fold split?" → README.md,
  "ML: Live Win-Probability Model" section, and the docstring at the top
  of `ml/train_win_predictor.py`.
- "Why isn't Deccan Chargers merged with Sunrisers Hyderabad?" →
  `etl/build_warehouse.py`, the comment block above `TEAM_NAME_MAP`.
  Different ownership, non-consecutive — BCCI terminated Deccan Chargers
  in 2012, SRH was awarded fresh in 2013.
- "What would you add with more time?" → Reasonable answers: player-level
  win-probability contribution (impact score per ball), auction-price
  vs. performance analysis if auction data were available, or a
  fielding-quality metric (currently unmodeled since the raw data has no
  fielding-position tracking).
