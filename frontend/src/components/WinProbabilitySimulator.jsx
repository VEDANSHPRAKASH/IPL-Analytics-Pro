import { useState } from "react";
import { api } from "../api/client.js";

const DEFAULT_VENUES = [
  "Wankhede Stadium",
  "M Chinnaswamy Stadium",
  "Eden Gardens",
  "MA Chidambaram Stadium, Chepauk",
  "Feroz Shah Kotla",
  "Sawai Mansingh Stadium",
];

export default function WinProbabilitySimulator({ teams }) {
  const [form, setForm] = useState({
    batting_team: "Mumbai Indians",
    bowling_team: "Chennai Super Kings",
    venue: "Wankhede Stadium",
    target: 180,
    runs_left: 45,
    balls_left: 36,
    wickets_left: 6,
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        ...form,
        target: Number(form.target),
        runs_left: Number(form.runs_left),
        balls_left: Number(form.balls_left),
        wickets_left: Number(form.wickets_left),
      };
      const res = await api.predictWinProbability(payload);
      setResult(res);
    } catch (e) {
      setError("Could not reach the prediction API. Is uvicorn running on :8000?");
    } finally {
      setLoading(false);
    }
  };

  const battingPct = result ? Math.round(result.batting_team_win_probability * 100) : 50;

  return (
    <div className="card">
      <p className="card-title">Live Win Probability Simulator</p>
      <p className="card-sub">
        Set a 2nd-innings match state and query the trained LightGBM model in real time
      </p>

      {error && <div className="error-banner">{error}</div>}

      <div className="simulator-grid">
        <div className="field">
          <label>Batting team (chasing)</label>
          <select value={form.batting_team} onChange={(e) => update("batting_team", e.target.value)}>
            {(teams.length ? teams : ["Mumbai Indians", "Chennai Super Kings"]).map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Bowling team</label>
          <select value={form.bowling_team} onChange={(e) => update("bowling_team", e.target.value)}>
            {(teams.length ? teams : ["Chennai Super Kings", "Mumbai Indians"]).map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Venue</label>
          <select value={form.venue} onChange={(e) => update("venue", e.target.value)}>
            {DEFAULT_VENUES.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Target score</label>
          <input type="number" value={form.target} onChange={(e) => update("target", e.target.value)} />
        </div>
        <div className="field">
          <label>Runs needed</label>
          <input type="number" value={form.runs_left} onChange={(e) => update("runs_left", e.target.value)} />
        </div>
        <div className="field">
          <label>Balls remaining</label>
          <input type="number" value={form.balls_left} onChange={(e) => update("balls_left", e.target.value)} />
        </div>
        <div className="field">
          <label>Wickets in hand</label>
          <input type="number" value={form.wickets_left} onChange={(e) => update("wickets_left", e.target.value)} />
        </div>
      </div>

      <button className="predict-btn" onClick={handlePredict} disabled={loading}>
        {loading ? "Querying model…" : "Predict win probability"}
      </button>

      {result && (
        <div className="win-bar-wrap">
          <div className="win-bar">
            <div
              className="win-bar-segment win-bar-batting"
              style={{ width: `${battingPct}%` }}
            >
              {battingPct > 12 && `${battingPct}%`}
            </div>
            <div
              className="win-bar-segment win-bar-bowling"
              style={{ width: `${100 - battingPct}%` }}
            >
              {100 - battingPct > 12 && `${100 - battingPct}%`}
            </div>
          </div>
          <div className="legend-row">
            <span>{result.batting_team}</span>
            <span>{result.bowling_team}</span>
          </div>
          <p className="footnote">
            Current run rate {result.current_run_rate} · Required run rate {result.required_run_rate}.
            Model evaluated on a season-holdout split (2023–24 unseen) — see /api/model-info for full metrics.
          </p>
        </div>
      )}
    </div>
  );
}
