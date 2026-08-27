
const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000/api";

async function get(path) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`);
  } catch (e) {
    throw new Error(
      `Cannot reach the API at ${BASE}. Is uvicorn running? (uvicorn api.main:app --reload --port 8000)`
    );
  }
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status} ${res.statusText}`);
  return res.json();
}

async function post(path, body) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new Error(
      `Cannot reach the API at ${BASE}. Is uvicorn running? (uvicorn api.main:app --reload --port 8000)`
    );
  }
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  teams: () => get("/teams"),
  teamLeaderboard: () => get("/teams/leaderboard"),
  topScorers: (limit = 10) => get(`/players/top-scorers?limit=${limit}`),
  topWicketTakers: (limit = 10) => get(`/players/top-wicket-takers?limit=${limit}`),
  venues: () => get("/venues"),
  headToHead: (team1, team2) =>
    get(`/head-to-head?team1=${encodeURIComponent(team1)}&team2=${encodeURIComponent(team2)}`),
  seasonChampions: () => get("/season-champions"),
  predictWinProbability: (payload) => post("/predict-win-probability", payload),
  modelInfo: () => get("/model-info"),
};
