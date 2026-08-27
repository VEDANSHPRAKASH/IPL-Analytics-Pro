export default function PlayerLeaderboard({ title, subtitle, rows, nameKey, valueKey, valueSuffix = "" }) {
  return (
    <div className="card">
      <p className="card-title">{title}</p>
      <p className="card-sub">{subtitle}</p>
      <div>
        {rows.map((row, i) => (
          <div className="stat-row" key={row[nameKey]}>
            <span>
              <span className="stat-rank">{i + 1}</span>
              <span className="stat-name">{row[nameKey]}</span>
            </span>
            <span className="stat-value">
              {row[valueKey]}
              {valueSuffix}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
