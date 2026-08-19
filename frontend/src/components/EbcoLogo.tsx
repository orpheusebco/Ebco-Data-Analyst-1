// EBCO brand mark, recreated as a self-contained SVG so it needs no external
// asset and stays crisp at any size. Swap in the official artwork by dropping a
// file at frontend/public/ebco-logo.svg and rendering an <img> instead.
export default function EbcoLogo({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 200 200"
      role="img"
      aria-label="EBCO"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect x="0" y="0" width="200" height="200" rx="26" fill="#1C4E9E" />
      {/* Elliptical ring */}
      <ellipse
        cx="100"
        cy="112"
        rx="86"
        ry="52"
        fill="none"
        stroke="#ffffff"
        strokeWidth="7"
      />
      {/* Wordmark */}
      <text
        x="100"
        y="112"
        textAnchor="middle"
        dominantBaseline="central"
        fill="#ffffff"
        fontFamily="ui-rounded, 'Segoe UI', system-ui, -apple-system, Arial, sans-serif"
        fontSize="76"
        fontWeight="700"
        letterSpacing="-2"
      >
        ebco
      </text>
      {/* Registered-trademark mark */}
      <g fill="none" stroke="#ffffff" strokeWidth="3.5">
        <circle cx="176" cy="52" r="12" />
      </g>
      <text
        x="176"
        y="53"
        textAnchor="middle"
        dominantBaseline="central"
        fill="#ffffff"
        fontFamily="'Segoe UI', system-ui, Arial, sans-serif"
        fontSize="13"
        fontWeight="700"
      >
        R
      </text>
    </svg>
  )
}
