import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function VenueChart({ data }) {
  const chartData = [...data].sort((a, b) => b.avg_first_innings_score - a.avg_first_innings_score).slice(0, 8);

  return (
    <div className="card" style={{ gridColumn: "span 2" }}>
      <p className="card-title">Venue Scoring Environment</p>
      <p className="card-sub">Average 1st-innings score — highest bars are the most batting-friendly grounds</p>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} margin={{ top: 10, right: 10 }}>
          <CartesianGrid stroke="#232d3d" vertical={false} />
          <XAxis
            dataKey="venue"
            tick={{ fill: "#8a96a8", fontSize: 10 }}
            angle={-20}
            textAnchor="end"
            height={70}
            interval={0}
          />
          <YAxis domain={[120, 200]} tick={{ fill: "#8a96a8", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "#171f2c", border: "1px solid #232d3d", borderRadius: 8 }}
            labelStyle={{ color: "#e9edf3" }}
          />
          <Bar dataKey="avg_first_innings_score" fill="#4a9d6a" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
