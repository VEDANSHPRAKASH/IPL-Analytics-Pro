import { useEffect, useState } from "react";
import { api } from "./api/client.js";
import SeamDivider from "./components/SeamDivider.jsx";
import TeamLeaderboard from "./components/TeamLeaderboard.jsx";
import PlayerLeaderboard from "./components/PlayerLeaderboard.jsx";
import VenueChart from "./components/VenueChart.jsx";
import WinProbabilitySimulator from "./components/WinProbabilitySimulator.jsx";
import SeasonChampions from "./components/SeasonChampions.jsx";

const TABS = ["Overview", "Players", "Win Predictor"];

export default function App() {
  const [tab, setTab] = useState("Overview");
  const [teams, setTeams] = useState([]);
  const [teamLeaderboard, setTeamLeaderboard] = useState([]);
  const [topScorers, setTopScorers] = useState([]);
  const [topBowlers, setTopBowlers] = useState([]);
  const [venues, setVenues] = useState([]);
  const [champions, setChampions] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [t, lb, scorers, bowlers, v, ch] = await Promise.all([
          api.teams(),
          api.teamLeaderboard(),
          api.topScorers(10),
          api.topWicketTakers(10),
          api.venues(),
          api.seasonChampions(),
        ]);
        setTeams(t);
        setTeamLeaderboard(lb);
        setTopScorers(scorers);
        setTopBowlers(bowlers);
        setVenues(v);
        setChampions(ch);
      } catch (e) {
        setError("Could not reach the API at :8000. Start it with: uvicorn api.main:app --reload");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="app-shell">
      <div className="hero">
        <div className="eyebrow">IPL Analytics Pro · SQL + ML Dashboard</div>
        <h1>Fourteen seasons, one warehouse.</h1>
        <p>
          260,000+ deliveries across 1,095 matches, normalized into a SQLite warehouse and served
          through a FastAPI backend — with a LightGBM model predicting live win probability from
          any 2nd-innings match state.
        </p>
      </div>

      <SeamDivider />

      {error && <div className="error-banner">{error}</div>}

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="loading-text">Loading warehouse data…</p>
      ) : (
        <>
          {tab === "Overview" && (
            <div className="grid">
              <TeamLeaderboard data={teamLeaderboard} />
              <VenueChart data={venues} />
              <SeasonChampions data={champions} />
            </div>
          )}

          {tab === "Players" && (
            <div className="grid">
              <PlayerLeaderboard
                title="Top Run Scorers"
                subtitle="Career runs across all seasons"
                rows={topScorers}
                nameKey="batter"
                valueKey="career_runs"
              />
              <PlayerLeaderboard
                title="Top Wicket Takers"
                subtitle="Career wickets, run-outs excluded"
                rows={topBowlers}
                nameKey="bowler"
                valueKey="wickets"
              />
            </div>
          )}

          {tab === "Win Predictor" && (
            <div className="grid">
              <WinProbabilitySimulator teams={teams} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
