export const hhmm = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false }) : "—";

export const dayTime = (iso: string | null | undefined) =>
  iso
    ? new Date(iso).toLocaleString([], {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      })
    : "—";

export function mins(value: number | null | undefined, digits = 0) {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(digits)}`;
}

/** "1 h 24 m" reads faster than "84 min" once you pass an hour. */
export function duration(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  const total = Math.round(value);
  if (total < 60) return `${total} min`;
  const h = Math.floor(total / 60);
  const m = total % 60;
  return m ? `${h} h ${m} m` : `${h} h`;
}

export const pct = (value: number | null | undefined) =>
  value === null || value === undefined ? "—" : `${Math.round(value)}%`;

export function sinceLabel(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 60000;
  if (diff < 1) return "just now";
  if (diff < 60) return `${Math.round(diff)} min ago`;
  const hours = diff / 60;
  if (hours < 24) return `${Math.round(hours)} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

export const titleCase = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const STATUS_TONE: Record<string, "ok" | "accent" | "caution" | "critical" | "info" | "neutral"> = {
  Completed: "ok",
  "In Progress": "accent",
  Ready: "info",
  "Not Started": "neutral",
  Blocked: "critical",
};
