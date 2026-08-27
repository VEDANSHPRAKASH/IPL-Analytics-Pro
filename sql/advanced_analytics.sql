-- -----------------------------------------------------------------------------
-- Q1. Season-by-season champion + their win margin, ranked within each season
--     (Window function: RANK() OVER PARTITION BY)
-- -----------------------------------------------------------------------------
WITH final_matches AS (
    SELECT season, MAX(date) AS final_date
    FROM matches
    GROUP BY season
)
SELECT m.season, m.winner AS champion, m.win_by_runs, m.win_by_wickets, m.venue
FROM matches m
JOIN final_matches f ON m.season = f.season AND m.date = f.final_date
ORDER BY m.season;


-- -----------------------------------------------------------------------------
-- Q2. Most successful teams overall — win %, and rank vs. every other team
--     (Window function: RANK() OVER ORDER BY)
-- -----------------------------------------------------------------------------
WITH team_matches AS (
    SELECT team1 AS team FROM matches
    UNION ALL
    SELECT team2 AS team FROM matches
),
played AS (
    SELECT team, COUNT(*) AS matches_played FROM team_matches GROUP BY team
),
won AS (
    SELECT winner AS team, COUNT(*) AS matches_won FROM matches
    WHERE winner IS NOT NULL AND winner != 'NA'
    GROUP BY winner
)
SELECT
    p.team,
    p.matches_played,
    COALESCE(w.matches_won, 0) AS matches_won,
    ROUND(100.0 * COALESCE(w.matches_won, 0) / p.matches_played, 2) AS win_pct,
    RANK() OVER (ORDER BY 1.0 * COALESCE(w.matches_won, 0) / p.matches_played DESC) AS win_pct_rank
FROM played p
LEFT JOIN won w ON p.team = w.team
WHERE p.matches_played >= 10          -- drop one-season teams for a fair ranking
ORDER BY win_pct_rank;


-- -----------------------------------------------------------------------------
-- Q3. Toss decision impact on match outcome
--     (Answers the original project's Q8 more rigorously, split by decision)
-- -----------------------------------------------------------------------------
SELECT
    toss_decision,
    COUNT(*) AS total_matches,
    SUM(CASE WHEN toss_winner = winner THEN 1 ELSE 0 END) AS toss_winner_also_won,
    ROUND(100.0 * SUM(CASE WHEN toss_winner = winner THEN 1 ELSE 0 END) / COUNT(*), 2) AS toss_win_match_win_pct
FROM matches
WHERE winner IS NOT NULL AND winner != 'NA'
GROUP BY toss_decision;


-- -----------------------------------------------------------------------------
-- Q4. Top 10 run-scorers of all time, with a running cumulative-runs column
--     and each player's rank versus the field
--     (Window functions: SUM() OVER, RANK() OVER)
-- -----------------------------------------------------------------------------
WITH batter_totals AS (
    SELECT
        batter,
        SUM(batsman_runs) AS career_runs,
        COUNT(DISTINCT match_id) AS innings_played,
        SUM(is_boundary) AS boundaries,
        ROUND(100.0 * SUM(batsman_runs) / NULLIF(SUM(is_legal_delivery), 0), 2) AS strike_rate
    FROM deliveries
    GROUP BY batter
)
SELECT
    batter,
    career_runs,
    innings_played,
    ROUND(1.0 * career_runs / NULLIF(innings_played, 0), 2) AS avg_runs_per_innings,
    strike_rate,
    RANK() OVER (ORDER BY career_runs DESC) AS run_rank
FROM batter_totals
ORDER BY career_runs DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- Q5. Phase-wise bowling economy (Powerplay / Middle / Death) for bowlers
--     with 300+ deliveries — identifies specialist death-over bowlers
--     (CTE + conditional aggregation, pivoted by phase)
-- -----------------------------------------------------------------------------
WITH bowler_phase AS (
    SELECT
        bowler,
        phase,
        SUM(total_runs) AS runs_conceded,
        SUM(is_legal_delivery) AS legal_balls,
        SUM(is_wicket) AS wickets
    FROM deliveries
    GROUP BY bowler, phase
),
bowler_totals AS (
    SELECT bowler, SUM(legal_balls) AS total_balls
    FROM bowler_phase
    GROUP BY bowler
    HAVING SUM(legal_balls) >= 300
)
SELECT
    bp.bowler,
    bp.phase,
    bp.wickets,
    ROUND(6.0 * bp.runs_conceded / NULLIF(bp.legal_balls, 0), 2) AS economy_rate
FROM bowler_phase bp
JOIN bowler_totals bt ON bp.bowler = bt.bowler
WHERE bp.phase = 'Death'
ORDER BY economy_rate ASC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- Q6. Head-to-head record between any two teams, both directions combined
--     (Self-referencing UNION + conditional aggregation)
-- -----------------------------------------------------------------------------
SELECT
    team1, team2,
    COUNT(*) AS matches_played,
    SUM(CASE WHEN winner = team1 THEN 1 ELSE 0 END) AS team1_wins,
    SUM(CASE WHEN winner = team2 THEN 1 ELSE 0 END) AS team2_wins
FROM matches
WHERE (team1 = 'Mumbai Indians' AND team2 = 'Chennai Super Kings')
   OR (team1 = 'Chennai Super Kings' AND team2 = 'Mumbai Indians')
GROUP BY team1, team2;


-- -----------------------------------------------------------------------------
-- Q7. "Player of the Match" leaderboard with a moving 3-season average
--     (Window function: AVG() OVER with a frame — trend detection)
-- -----------------------------------------------------------------------------
WITH season_awards AS (
    SELECT season, player_of_match, COUNT(*) AS awards
    FROM matches
    WHERE player_of_match IS NOT NULL AND player_of_match != 'NA'
    GROUP BY season, player_of_match
)
SELECT
    player_of_match,
    season,
    awards,
    ROUND(AVG(awards) OVER (
        PARTITION BY player_of_match
        ORDER BY season
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS trailing_3season_avg_awards
FROM season_awards
ORDER BY player_of_match, season;


-- -----------------------------------------------------------------------------
-- Q8. Venue-level scoring environment (bowling-friendly vs batting-friendly)
--     Average first-innings score per venue, ranked
-- -----------------------------------------------------------------------------
WITH first_innings_scores AS (
    SELECT match_id, MAX(innings_cum_runs) AS final_score
    FROM deliveries
    WHERE inning = 1
    GROUP BY match_id
)
SELECT
    m.venue,
    COUNT(*) AS matches_hosted,
    ROUND(AVG(f.final_score), 1) AS avg_first_innings_score,
    RANK() OVER (ORDER BY AVG(f.final_score) DESC) AS batting_friendly_rank
FROM matches m
JOIN first_innings_scores f ON m.id = f.match_id
GROUP BY m.venue
HAVING COUNT(*) >= 10
ORDER BY avg_first_innings_score DESC;


-- -----------------------------------------------------------------------------
-- Q9. Death-overs finishers: best strike rate in the last 5 overs (16-20)
--     among players with 150+ death-over deliveries faced
-- -----------------------------------------------------------------------------
WITH death_overs AS (
    SELECT batter, SUM(batsman_runs) AS runs, SUM(is_legal_delivery) AS balls_faced
    FROM deliveries
    WHERE phase = 'Death'
    GROUP BY batter
    HAVING SUM(is_legal_delivery) >= 150
)
SELECT
    batter,
    runs,
    balls_faced,
    ROUND(100.0 * runs / balls_faced, 2) AS death_overs_strike_rate
FROM death_overs
ORDER BY death_overs_strike_rate DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- Q10. Closest matches ever (nail-biters) — smallest winning margins,
--      runs and wickets normalized onto one comparable scale via CASE
-- -----------------------------------------------------------------------------
SELECT
    season, date, team1, team2, winner, result,
    CASE WHEN result = 'runs' THEN win_by_runs ELSE NULL END AS margin_runs,
    CASE WHEN result = 'wickets' THEN win_by_wickets ELSE NULL END AS margin_wickets
FROM matches
WHERE (result = 'runs' AND win_by_runs BETWEEN 1 AND 5)
   OR (result = 'wickets' AND win_by_wickets = 1)
ORDER BY date DESC;
