/**
 * Signature visual element: a cricket-ball seam rendered as a section
 * divider — two parallel stitched lines that echo the ball's seam,
 * instead of a generic <hr>.
 */
export default function SeamDivider() {
  return (
    <svg className="seam-divider" viewBox="0 0 1180 20" preserveAspectRatio="none">
      <line x1="0" y1="7" x2="1180" y2="7" stroke="#232d3d" strokeWidth="1" />
      <line x1="0" y1="13" x2="1180" y2="13" stroke="#232d3d" strokeWidth="1" />
      {Array.from({ length: 59 }).map((_, i) => (
        <line
          key={i}
          x1={i * 20 + 4}
          y1="5"
          x2={i * 20 + 10}
          y2="15"
          stroke="#f0b429"
          strokeWidth="1.4"
          opacity="0.55"
        />
      ))}
    </svg>
  );
}
