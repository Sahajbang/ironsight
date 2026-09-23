import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from "react";

import { Icon, type IconName } from "./Icon";
import "./neu.css";

export { Icon };
export type { IconName };

/* ---------------- Card ---------------- */

export function Card({
  children,
  title,
  icon,
  action,
  variant,
  className = "",
  style,
}: {
  children: ReactNode;
  title?: string;
  icon?: IconName;
  action?: ReactNode;
  variant?: "tight" | "flush" | "flat" | "inset";
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <section className={`card ${variant ? `card--${variant}` : ""} ${className}`} style={style}>
      {(title || action) && (
        <header className="card__head">
          {title && (
            <h2 className="card__title">
              {icon && <Icon name={icon} size={16} />}
              {title}
            </h2>
          )}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

/* ---------------- Button ---------------- */

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "active";
  size?: "sm";
  block?: boolean;
  icon?: IconName;
};

export function Button({ variant, size, block, icon, children, className = "", ...rest }: BtnProps) {
  return (
    <button
      className={[
        "btn",
        variant ? `btn--${variant}` : "",
        size ? `btn--${size}` : "",
        block ? "btn--block" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...rest}
    >
      {icon && <Icon name={icon} size={size === "sm" ? 15 : 17} />}
      {children}
    </button>
  );
}

export function IconButton({
  icon,
  label,
  round,
  small,
  active,
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  icon: IconName;
  label: string;
  round?: boolean;
  small?: boolean;
  active?: boolean;
}) {
  return (
    <button
      className={`iconbtn ${round ? "iconbtn--round" : ""} ${small ? "iconbtn--sm" : ""} ${className}`}
      data-active={active || undefined}
      aria-label={label}
      title={label}
      {...rest}
    >
      <Icon name={icon} size={small ? 16 : 19} />
    </button>
  );
}

/* ---------------- Badge ---------------- */

export type Tone = "critical" | "warning" | "caution" | "info" | "ok" | "accent" | "neutral";

/** Map backend severity strings onto the visual tone scale. */
export function severityTone(severity?: string): Tone {
  switch (severity) {
    case "Critical":
      return "critical";
    case "Warning":
      return "warning";
    case "Caution":
      return "caution";
    case "Informational":
      return "info";
    default:
      return "neutral";
  }
}

export function Badge({
  children,
  tone = "neutral",
  dot = true,
  icon,
}: {
  children: ReactNode;
  tone?: Tone;
  dot?: boolean;
  icon?: IconName;
}) {
  return (
    <span className={`badge ${tone !== "neutral" ? `badge--${tone}` : ""}`}>
      {icon ? <Icon name={icon} size={12} /> : dot && tone !== "neutral" && <i className="badge__dot" />}
      {children}
    </span>
  );
}

/* ---------------- Toggle ---------------- */

export function Toggle({
  on,
  onChange,
  label,
}: {
  on: boolean;
  onChange: (next: boolean) => void;
  label: string;
}) {
  return (
    <button
      className="toggle"
      data-on={on}
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={() => onChange(!on)}
    >
      <span className="toggle__thumb" />
    </button>
  );
}

/* ---------------- Meter ---------------- */

export function Meter({ value, tone }: { value: number; tone?: "critical" | "warning" | "ok" }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="meter" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
      <div className={`meter__fill ${tone ? `meter__fill--${tone}` : ""}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

/* ---------------- Knob gauge ---------------- */

const KNOB_R = 42;
const KNOB_CIRC = 2 * Math.PI * KNOB_R;
const KNOB_SWEEP = 0.75; // 270° dial, like an instrument panel rather than a full ring

/** A dial you read at a glance: value as an arc, the number in the middle, nothing else.
 *  Concentric raised-then-inset rings are what make it read as a physical knob. */
export function Knob({
  value,
  max = 100,
  display,
  unit,
  tone = "accent",
  size = 116,
}: {
  value: number;
  max?: number;
  display?: string;
  unit?: string;
  tone?: Tone;
  size?: number;
}) {
  const fraction = Math.max(0, Math.min(1, max === 0 ? 0 : value / max));
  const color = tone === "neutral" ? "var(--text-muted)" : `var(--${tone === "accent" ? "accent" : tone})`;

  return (
    <div className="knob" style={{ width: size, height: size }}>
      <div className="knob__rim">
        <div className="knob__face">
          <svg viewBox="0 0 100 100" className="knob__svg">
            <circle
              cx="50"
              cy="50"
              r={KNOB_R}
              fill="none"
              stroke="var(--surface-deep)"
              strokeWidth="7"
              strokeLinecap="round"
              strokeDasharray={`${KNOB_CIRC * KNOB_SWEEP} ${KNOB_CIRC}`}
              transform="rotate(135 50 50)"
            />
            <circle
              cx="50"
              cy="50"
              r={KNOB_R}
              fill="none"
              stroke={color}
              strokeWidth="7"
              strokeLinecap="round"
              strokeDasharray={`${KNOB_CIRC * KNOB_SWEEP * fraction} ${KNOB_CIRC}`}
              transform="rotate(135 50 50)"
              style={{ transition: "stroke-dasharray 400ms cubic-bezier(0.22,0.61,0.36,1)" }}
            />
          </svg>
          <div className="knob__center">
            <span className="knob__value">{display ?? Math.round(value)}</span>
            {unit && <span className="knob__unit">{unit}</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

/** Square module that opens to show its detail — the glanceable number stays, the
 *  explanation is one tap away instead of permanently taking up room. */
export function GaugeTile({
  label,
  children,
  detail,
  open,
  onToggle,
  footer,
}: {
  label: string;
  children: ReactNode;
  detail?: ReactNode;
  open?: boolean;
  onToggle?: () => void;
  footer?: ReactNode;
}) {
  return (
    <div className={`gtile ${open ? "gtile--open" : ""}`}>
      <button className="gtile__main" onClick={onToggle} aria-expanded={!!open} disabled={!detail}>
        <span className="label">{label}</span>
        {children}
        {footer && <span className="gtile__foot">{footer}</span>}
        {detail && (
          <span className="gtile__chev">
            <Icon name="chevronDown" size={14} />
          </span>
        )}
      </button>
      {open && detail && <div className="gtile__detail">{detail}</div>}
    </div>
  );
}

/* ---------------- Tabs ---------------- */

export function Tabs<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (next: T) => void;
}) {
  return (
    <div className="tabs" role="tablist">
      {options.map((opt) => (
        <button
          key={opt.value}
          className="tabs__tab"
          role="tab"
          aria-selected={value === opt.value}
          data-active={value === opt.value}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

/* ---------------- Stat ---------------- */

export function Stat({
  label,
  value,
  unit,
  tone,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  tone?: Tone;
}) {
  const color =
    tone && tone !== "neutral" ? { color: `var(--${tone === "accent" ? "accent-deep" : tone})` } : undefined;
  return (
    <div className="col" style={{ gap: 2 }}>
      <span className="label">{label}</span>
      <span className="stat__value" style={color}>
        {value}
        {unit && <span className="stat__unit">{unit}</span>}
      </span>
    </div>
  );
}

/* ---------------- Empty / Loading ---------------- */

export function Empty({ icon = "info", children }: { icon?: IconName; children: ReactNode }) {
  return (
    <div className="empty">
      <Icon name={icon} size={26} />
      <span style={{ fontSize: "0.88rem" }}>{children}</span>
    </div>
  );
}

export function Skeleton({ h = 16, w = "100%", style }: { h?: number; w?: string | number; style?: CSSProperties }) {
  return <div className="skel" style={{ height: h, width: w, ...style }} />;
}

export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="col" style={{ gap: 12 }}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} h={i === 0 ? 22 : 14} w={i === 0 ? "45%" : `${70 + ((i * 13) % 25)}%`} />
      ))}
    </div>
  );
}
