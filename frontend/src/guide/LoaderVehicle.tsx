/* Cat-style wheel loader, drawn as SVG so it can be animated part-by-part.
 *
 * The whole UI is deliberately achromatic except for one rationed yellow accent — this
 * machine IS that accent, made physical. That is why it reads as an event when it drives
 * in, and why it has to leave again afterwards rather than parking on screen.
 */
import { motion } from "framer-motion";

export function LoaderVehicle({
  boomAngle = 0,
  driving = false,
  bucketLoaded = true,
  size = 132,
}: {
  boomAngle?: number;
  driving?: boolean;
  bucketLoaded?: boolean;
  size?: number;
}) {
  const wheelSpin = driving
    ? { rotate: 360, transition: { repeat: Infinity, duration: 0.7, ease: "linear" as const } }
    : { rotate: 0 };

  return (
    <svg
      width={size}
      height={size * (80 / 140)}
      viewBox="0 0 140 80"
      fill="none"
      aria-hidden="true"
      style={{ overflow: "visible", display: "block" }}
    >
      <defs>
        <linearGradient id="ls-body" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FFD94A" />
          <stop offset="55%" stopColor="#F5C518" />
          <stop offset="100%" stopColor="#D9A400" />
        </linearGradient>
        <linearGradient id="ls-steel" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#585F6B" />
          <stop offset="100%" stopColor="#343a44" />
        </linearGradient>
      </defs>

      {/* soft contact shadow on the ground */}
      <ellipse cx="70" cy="76" rx="52" ry="4.5" fill="rgba(120,133,152,0.28)" />

      {/* ---------- boom + bucket (rotates about the chassis pivot) ---------- */}
      <motion.g
        animate={{ rotate: boomAngle }}
        transition={{ type: "spring", stiffness: 90, damping: 14 }}
        style={{ transformOrigin: "64px 44px" }}
      >
        {/* boom arm */}
        <path d="M64 44 L112 30 L118 37 L70 51 Z" fill="url(#ls-steel)" />
        {/* hydraulic ram */}
        <path d="M70 50 L100 41" stroke="#8b93a1" strokeWidth="3.4" strokeLinecap="round" />
        <circle cx="64" cy="44" r="4.2" fill="#22262d" />

        {/* bucket */}
        <g>
          <path
            d="M112 26 L136 20 L139 33 Q136 44 124 46 L112 40 Z"
            fill="url(#ls-body)"
            stroke="#B88A00"
            strokeWidth="1.1"
          />
          {/* cutting edge teeth */}
          <path d="M136 20 L139 25 M131 21.3 L133.5 26.2" stroke="#8a6c10" strokeWidth="1.6" strokeLinecap="round" />
          {bucketLoaded && (
            <path d="M115 27.5 Q124 21 133.5 23.5" stroke="#6b7684" strokeWidth="2.6" strokeLinecap="round" opacity="0.55" />
          )}
        </g>
      </motion.g>

      {/* ---------- rear body ---------- */}
      <path d="M17 36 Q17 31 22 31 L58 31 L60 54 L19 54 Q17 54 17 50 Z" fill="url(#ls-body)" />
      {/* counterweight */}
      <path d="M13 38 Q13 35 16 35 L18 35 L18 52 L16 52 Q13 52 13 49 Z" fill="url(#ls-steel)" />
      {/* exhaust stack */}
      <rect x="27" y="19" width="5" height="13" rx="2" fill="#4a515c" />

      {/* ---------- cab ---------- */}
      <path d="M38 12 L57 14 L58 31 L36 31 Z" fill="url(#ls-body)" />
      <path d="M40.5 16.5 L54.5 17.8 L55.2 28.5 L39.8 28.5 Z" fill="#CBE0F0" opacity="0.92" />
      {/* ROPS posts */}
      <path d="M38 12 L36 31 M57 14 L58 31" stroke="#3a3f47" strokeWidth="2.2" strokeLinecap="round" />

      {/* ---------- front chassis + articulation ---------- */}
      <path d="M60 38 L98 38 L98 54 L60 54 Z" fill="url(#ls-body)" />
      <path d="M60 38 L60 54" stroke="#B88A00" strokeWidth="1.6" />

      {/* ---------- wheels ---------- */}
      {[
        { cx: 34, cy: 58 },
        { cx: 92, cy: 58 },
      ].map((w) => (
        <g key={w.cx}>
          <circle cx={w.cx} cy={w.cy} r="16" fill="#2b3038" />
          <circle cx={w.cx} cy={w.cy} r="15.2" fill="none" stroke="#1d2128" strokeWidth="1.6" />
          <motion.g animate={wheelSpin} style={{ transformOrigin: `${w.cx}px ${w.cy}px` }}>
            <circle cx={w.cx} cy={w.cy} r="7.4" fill="#C9CFD8" />
            <circle cx={w.cx} cy={w.cy} r="3" fill="#8b93a1" />
            {/* tread blocks so rotation is actually visible */}
            {Array.from({ length: 8 }).map((_, i) => {
              const a = (i / 8) * Math.PI * 2;
              return (
                <rect
                  key={i}
                  x={w.cx + Math.cos(a) * 12.4 - 1.5}
                  y={w.cy + Math.sin(a) * 12.4 - 2.4}
                  width="3"
                  height="4.8"
                  rx="1.2"
                  fill="#4a515c"
                  transform={`rotate(${(a * 180) / Math.PI + 90} ${w.cx + Math.cos(a) * 12.4} ${w.cy + Math.sin(a) * 12.4})`}
                />
              );
            })}
          </motion.g>
        </g>
      ))}
    </svg>
  );
}

/** Simplified silhouette for the 40px toggle button — detail at that size just turns to mud. */
export function LoaderGlyph({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ display: "block" }}>
      <path d="M13.2 11.4 19 9.6l1 3.4-4.6 1.6-2.2-1.4Z" fill="currentColor" />
      <path d="M6.6 12.2 13.6 10.2" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
      <path d="M3.6 10.2h6.2v5.4H3.6z" fill="currentColor" />
      <path d="M5.4 6.6h3.4l.6 3.6H5z" fill="currentColor" />
      <path d="M9.8 12.4h4v3.2h-4z" fill="currentColor" />
      <circle cx="6.4" cy="17.4" r="2.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="14.4" cy="17.4" r="2.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}
