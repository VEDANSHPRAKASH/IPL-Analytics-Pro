export default function SeasonChampions({ data }) {
  return (
    <div className="card" style={{ gridColumn: "span 2" }}>
      <p className="card-title">Season Champions</p>
      <p className="card-sub">Final-match winner for every IPL season on record</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        {data.map((row) => (
          <div
            key={row.season}
            style={{
              background: "var(--surface-raised)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "10px 14px",
              minWidth: 150,
            }}
          >
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-faint)" }}>
              {row.season}
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>{row.champion}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
