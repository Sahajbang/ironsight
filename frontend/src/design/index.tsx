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
