import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function TeamLeaderboard({ data }) {
  const chartData = [...data].sort((a, b) => b.win_pct - a.win_pct).slice(0, 8);

  return (
    <div className="card">
      <p className="card-title">Team Win % Leaderboard</p>
      <p className="card-sub">Franchises with 10+ matches played, name-normalized across relocations/renames</p>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20 }}>
          <CartesianGrid stroke="#232d3d" horizontal={false} />
          <XAxis type="number" domain={[0, 70]} tick={{ fill: "#8a96a8", fontSize: 11 }} />
          <YAxis
            type="category"
            dataKey="team"
            width={150}
            tick={{ fill: "#e9edf3", fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{ background: "#171f2c", border: "1px solid #232d3d", borderRadius: 8 }}
            labelStyle={{ color: "#e9edf3" }}
            formatter={(v) => [`${v}%`, "Win rate"]}
          />
          <Bar dataKey="win_pct" fill="#f0b429" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
