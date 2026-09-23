/* Thin-stroke outline icons, drawn here rather than pulled from a library.
 * One component with a path registry keeps the bundle small and guarantees a consistent
 * stroke weight, which matters a lot on a soft surface — mixed weights read as sloppy. */
import type { CSSProperties } from "react";

export type IconName =
  | "gauge"
  | "map"
  | "list"
  | "shield"
  | "book"
  | "chart"
  | "clock"
  | "alert"
  | "search"
  | "chevronRight"
  | "chevronDown"
  | "close"
  | "check"
  | "play"
  | "plus"
  | "send"
  | "chat"
  | "info"
  | "fuel"
  | "wrench"
  | "user"
  | "excavator"
  | "cursor"
  | "calendar"
  | "video"
  | "file"
  | "sim"
  | "refresh"
  | "target"
  | "bolt"
  | "idle"
  | "wifi"
  | "droplet"
  | "wind";

const P: Record<IconName, React.ReactNode> = {
  gauge: (
    <>
      <path d="M12 14.5 16 9" />
      <circle cx="12" cy="14.5" r="1.4" />
      <path d="M3.6 17.5a9.5 9.5 0 1 1 16.8 0" />
    </>
  ),
  map: (
    <>
      <path d="M9 4 3.6 6.3v13.4L9 17.4l6 2.3 5.4-2.3V4L15 6.3 9 4Z" />
      <path d="M9 4v13.4M15 6.3v13.4" />
    </>
  ),
  list: (
    <>
      <path d="M8.5 6.5h11M8.5 12h11M8.5 17.5h11" />
      <path d="M4.2 6.5h.01M4.2 12h.01M4.2 17.5h.01" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3.2 5 6v5.6c0 4.2 2.9 7.6 7 9.2 4.1-1.6 7-5 7-9.2V6l-7-2.8Z" />
      <path d="m9.2 12 2 2 3.6-3.8" />
    </>
  ),
  book: (
    <>
      <path d="M4.5 5.2A1.7 1.7 0 0 1 6.2 3.5H19v14.3H6.2a1.7 1.7 0 0 0-1.7 1.7V5.2Z" />
      <path d="M4.5 17.8a1.7 1.7 0 0 0 1.7 1.7H19" />
      <path d="M8.2 7.6h6.4" />
    </>
  ),
  chart: (
    <>
      <path d="M4 19.5h16" />
      <path d="M7 19.5v-6M12 19.5V6.5M17 19.5v-9" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M12 7.2V12l3.2 1.9" />
    </>
  ),
  alert: (
    <>
      <path d="M10.6 4.3 3.2 17.1a1.6 1.6 0 0 0 1.4 2.4h14.8a1.6 1.6 0 0 0 1.4-2.4L13.4 4.3a1.6 1.6 0 0 0-2.8 0Z" />
      <path d="M12 9.6v4M12 16.6h.01" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="6.8" />
      <path d="m16.2 16.2 4 4" />
    </>
  ),
  chevronRight: <path d="m9.5 5.5 6.5 6.5-6.5 6.5" />,
  chevronDown: <path d="m5.5 9.5 6.5 6.5 6.5-6.5" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  check: <path d="m5 12.5 4.5 4.5L19 7" />,
  play: <path d="M8 5.6 18 12 8 18.4V5.6Z" />,
  plus: <path d="M12 5.5v13M5.5 12h13" />,
  send: (
    <>
      <path d="M20.5 3.5 10.8 13.2" />
      <path d="M20.5 3.5 14.3 20.5l-3.5-7.3-7.3-3.5L20.5 3.5Z" />
    </>
  ),
  chat: (
    <>
      <path d="M20.5 11.6c0 4-3.8 7.2-8.5 7.2a9.8 9.8 0 0 1-2.7-.4L4 20.5l1.5-3.9a6.9 6.9 0 0 1-2-4.9c0-4 3.8-7.2 8.5-7.2s8.5 3.2 8.5 7.1Z" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M12 11.2v5M12 7.9h.01" />
    </>
  ),
  fuel: (
    <>
      <path d="M5 20.5V5.3A1.8 1.8 0 0 1 6.8 3.5h4.9a1.8 1.8 0 0 1 1.8 1.8v15.2" />
      <path d="M3.8 20.5h11" />
      <path d="M5 11.4h8.5" />
      <path d="M13.5 8.2h3a2 2 0 0 1 2 2v6a1.6 1.6 0 0 0 3.2 0v-5.4l-2.2-2.8" />
    </>
  ),
  wrench: (
    <>
      <path d="M15.2 3.9a5 5 0 0 0-5.9 6.6L3.9 15.9a2 2 0 0 0 2.8 2.8l5.4-5.4a5 5 0 0 0 6.6-5.9l-2.9 2.9-2.8-.7-.7-2.8 2.9-2.9Z" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8.2" r="3.9" />
      <path d="M4.8 20.2a7.6 7.6 0 0 1 14.4 0" />
    </>
  ),
  excavator: (
    <>
      <path d="M3.2 19.3h13.4" />
      <circle cx="6.2" cy="17.2" r="2.1" />
      <circle cx="13.4" cy="17.2" r="2.1" />
      <path d="M4.6 15V11h7.6v4" />
      <path d="M8.4 11V8.4h3.8" />
      <path d="m12.2 9.4 4.6-3.2 3.6 5.2" />
      <path d="m20.4 11.4-1.2 3.4-3.4-1" />
    </>
  ),
  cursor: <path d="m5.5 3.8 5.2 16.4 2.6-6.6 6.6-2.6L5.5 3.8Z" />,
  calendar: (
    <>
      <rect x="3.6" y="5.4" width="16.8" height="15" rx="2.2" />
      <path d="M3.6 10h16.8M8.2 3.5v3.6M15.8 3.5v3.6" />
    </>
  ),
  video: (
    <>
      <rect x="3" y="6" width="12.5" height="12" rx="2.4" />
      <path d="m15.5 13 5.5 3.3V7.7L15.5 11v2Z" />
    </>
  ),
  file: (
    <>
      <path d="M13.5 3.6H7.2a2 2 0 0 0-2 2v12.8a2 2 0 0 0 2 2h9.6a2 2 0 0 0 2-2V9l-5.3-5.4Z" />
      <path d="M13.4 3.6V9h5.4M8.8 13.3h6.4M8.8 16.6h4.4" />
    </>
  ),
  sim: (
    <>
      <rect x="2.8" y="5.2" width="18.4" height="12.2" rx="2.4" />
      <path d="M8.6 20.5h6.8M12 17.4v3.1" />
      <path d="M7.4 11.3h2.8M8.8 9.9v2.8" />
      <circle cx="15.6" cy="10.4" r="0.9" />
      <circle cx="17.6" cy="12.6" r="0.9" />
    </>
  ),
  refresh: (
    <>
      <path d="M20 12a8 8 0 1 1-2.6-5.9" />
      <path d="M20.4 4.2v4.4H16" />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="8.4" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r="0.9" />
    </>
  ),
  bolt: <path d="M13.4 2.8 5 13.6h6l-.9 7.6L19 10.4h-6.2l.6-7.6Z" />,
  idle: (
    <>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M9.6 9.4v5.2M14.4 9.4v5.2" />
    </>
  ),
  wifi: (
    <>
      <path d="M2.6 9.2a14 14 0 0 1 18.8 0" />
      <path d="M6 12.6a9.2 9.2 0 0 1 12 0" />
      <path d="M9.3 16a4.6 4.6 0 0 1 5.4 0" />
      <path d="M12 19.3h.01" />
    </>
  ),
  droplet: <path d="M12 3.4 6.9 9.9a6.6 6.6 0 1 0 10.2 0L12 3.4Z" />,
  wind: (
    <>
      <path d="M3.6 8.6h9.2a2.8 2.8 0 1 0-2.8-2.8" />
      <path d="M3.6 13h12.6a2.8 2.8 0 1 1-2.8 2.8" />
      <path d="M3.6 17.4h5.8" />
    </>
  ),
};

export function Icon({
  name,
  size = 20,
  style,
  className,
  strokeWidth = 1.7,
}: {
  name: IconName;
  size?: number;
  style?: CSSProperties;
  className?: string;
  strokeWidth?: number;
}) {
  const filled = name === "cursor" || name === "play" || name === "bolt";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={filled ? 0 : strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
      style={{ flexShrink: 0, display: "block", ...style }}
    >
      {P[name]}
    </svg>
  );
}
