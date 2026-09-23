import { useState } from "react";

import { useSiteMap, type SiteOperator } from "../api/client";
import { Badge, Card, CardSkeleton, Empty, Icon, Meter, Stat, Tabs, severityTone } from "../design";
import { sinceLabel, titleCase } from "../lib/format";
import { useApp } from "../state/store";
import "./pages.css";

const STATE_TONE: Record<string, "ok" | "caution" | "critical" | "info" | "neutral"> = {
  Active: "ok",
  Idle: "caution",
  Blocked: "critical",
  Break: "info",
  Incident: "critical",
};

const ZONE_FILL: Record<string, string> = {
  excavation: "#d7dee8",
  active: "rgba(245,197,24,0.16)",
  loading: "#d7dee8",
  storage: "#dae0e9",
  restricted: "rgba(192,57,43,0.10)",
  parking: "#dae0e9",
};

export function SiteMap() {
  const { operatorId } = useApp();
  const [view, setView] = useState<"operator" | "supervisor">("supervisor");
  const { data, isLoading } = useSiteMap(operatorId, view);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = data?.operators.find((o) => o.operator_id === selectedId) ?? null;

  return (
    <div className="page__grid">
      <Card
        title={`Jobsite · tick ${data?.tick ?? 0}`}
        icon="map"
        action={
          <Tabs
            value={view}
            onChange={setView}
            options={[
              { value: "supervisor", label: "Supervisor" },
              { value: "operator", label: "Operator" },
            ]}
          />
        }
      >
        {isLoading || !data ? (
          <CardSkeleton rows={6} />
        ) : (
          <div className="sitemap" data-guide-id="site-map">
            <svg className="sitemap__svg" viewBox="0 0 100 62.5" preserveAspectRatio="none">
              <defs>
                <pattern id="restricted-hatch" width="3" height="3" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
                  <line x1="0" y1="0" x2="0" y2="3" stroke="rgba(192,57,43,0.32)" strokeWidth="1" />
                </pattern>
              </defs>

              {/* haul route */}
              <polyline
                points={data.haul_route.map(([x, y]) => `${x * 100},${y * 62.5}`).join(" ")}
                fill="none"
                stroke="#c6cfdb"
                strokeWidth="3.2"
                strokeLinecap="round"
              />
              <polyline
                points={data.haul_route.map(([x, y]) => `${x * 100},${y * 62.5}`).join(" ")}
                fill="none"
                stroke="#eef2f7"
                strokeWidth="0.5"
                strokeDasharray="2 2"
              />

              {/* zones */}
              {data.zones.map((z) => (
                <g key={z.id}>
                  <rect
                    x={z.x * 100}
                    y={z.y * 62.5}
                    width={z.w * 100}
                    height={z.h * 62.5}
                    rx="2"
                    fill={ZONE_FILL[z.kind] ?? "#d7dee8"}
                  />
                  {z.kind === "restricted" && (
                    <rect
                      x={z.x * 100}
                      y={z.y * 62.5}
                      width={z.w * 100}
                      height={z.h * 62.5}
                      rx="2"
                      fill="url(#restricted-hatch)"
                    />
                  )}
                  <text
                    x={z.x * 100 + 1.6}
                    y={z.y * 62.5 + 3.4}
                    fontSize="1.9"
                    fill={z.kind === "restricted" ? "#a33528" : "#8b95a5"}
                    fontWeight="600"
                    style={{ letterSpacing: "0.08em", textTransform: "uppercase" }}
                  >
                    {z.label}
                  </text>
                </g>
              ))}
            </svg>

            {/* hazards */}
            {data.hazards.map((h) => (
              <div key={h.id} className="hazard" style={{ left: `${h.x * 100}%`, top: `${h.y * 100}%` }} title={h.message}>
                <Icon name="alert" size={18} />
              </div>
            ))}

            {/* operators */}
            {data.operators.map((op) => (
              <button
                key={op.operator_id}
                className={`marker ${op.operator_id === selectedId ? "marker--selected" : ""} marker--${severityTone(
                  op.safety_state,
                )}`}
                style={{ left: `${op.x * 100}%`, top: `${op.y * 100}%` }}
                onClick={() => setSelectedId(op.operator_id === selectedId ? null : op.operator_id)}
              >
                {op.safety_state !== "Normal" && <span className="marker__pulse" />}
                <span className="marker__body">
                  <span
                    className="badge__dot"
                    style={{ background: `var(--${STATE_TONE[op.operating_state] ?? "info"})` }}
                  />
                  {op.operator_name.split(" ")[0]}
                  {op.operator_id === operatorId && " (you)"}
                </span>
              </button>
            ))}
          </div>
        )}
      </Card>

      <div className="col" style={{ gap: "var(--s5)" }}>
        {selected ? (
          <OperatorDetail op={selected} isSelf={selected.operator_id === operatorId} />
        ) : (
          <Card title="Site state" icon="gauge">
            <div className="stack">
              {(data?.operators ?? []).map((op) => (
                <button
                  key={op.operator_id}
                  className="slot"
                  style={{ width: "100%", textAlign: "left" }}
                  onClick={() => setSelectedId(op.operator_id)}
                >
                  <span className="col grow" style={{ gap: 1 }}>
                    <strong style={{ fontSize: "0.85rem" }}>{op.operator_name}</strong>
                    <span className="muted" style={{ fontSize: "0.72rem" }}>
                      {op.zone} · {op.machine_id ?? "—"}
                    </span>
                  </span>
                  <Badge tone={STATE_TONE[op.operating_state] ?? "info"}>{op.operating_state}</Badge>
                </button>
              ))}
              {data?.operators.length === 0 && <Empty icon="map">No operators in view.</Empty>}
            </div>
          </Card>
        )}

        <Card title="Live event feed" icon="list">
          <div className="feed">
            {(data?.recent_events ?? []).length === 0 && <Empty icon="clock">Waiting for site events…</Empty>}
            {(data?.recent_events ?? [])
              .slice()
              .reverse()
              .map((e, i) => (
                <div key={`${e.tick}-${i}`} className="feed__row">
                  <span className="feed__tick">#{e.tick}</span>
                  <span className="col grow" style={{ gap: 1 }}>
                    <strong style={{ fontSize: "0.78rem", fontWeight: 500 }}>{e.message}</strong>
                    <span className="muted" style={{ fontSize: "0.68rem" }}>
                      {titleCase(e.event_type)} · {e.operator_id} · {sinceLabel(e.timestamp)}
                    </span>
                  </span>
                </div>
              ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function OperatorDetail({ op, isSelf }: { op: SiteOperator; isSelf: boolean }) {
  return (
    <Card
      title={isSelf ? "You" : "Operator"}
      icon="user"
      action={<Badge tone={STATE_TONE[op.operating_state] ?? "info"}>{op.operating_state}</Badge>}
    >
      <div className="col" style={{ gap: "var(--s4)" }}>
        <div className="col" style={{ gap: 2 }}>
          <h2 style={{ fontSize: "1.1rem" }}>{op.operator_name}</h2>
          <span className="muted" style={{ fontSize: "0.78rem" }}>
            {op.machine_type ?? "—"} {op.machine_id ?? ""} · {op.zone}
          </span>
        </div>

        <div className="col" style={{ gap: 6 }}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span className="label">Workload</span>
            <span style={{ fontSize: "0.8rem", fontWeight: 700 }}>{Math.round(op.workload_score)}</span>
          </div>
          <Meter
            value={op.workload_score}
            tone={op.workload_score > 80 ? "warning" : op.workload_score < 25 ? undefined : "ok"}
          />
          <span className="muted" style={{ fontSize: "0.72rem" }}>
            {op.workload_score > 80
              ? "Elevated — queued work is building up."
              : op.workload_score < 25
                ? "Low — idle or between tasks."
                : "Normal for this point in the shift."}
          </span>
        </div>

        <div className="sumgrid">
          <Stat label="Task" value={op.current_task_id ?? "—"} />
          <Stat label="Task status" value={op.task_status} />
          <Stat
            label="Seatbelt"
            value={op.seatbelt_status}
            tone={op.seatbelt_status === "Fastened" ? "ok" : "critical"}
          />
          <Stat
            label="Proximity"
            value={`${op.proximity_distance_m} m`}
            tone={op.proximity_distance_m < 3 ? "critical" : op.proximity_distance_m < 6 ? "warning" : "ok"}
          />
        </div>

        {op.safety_state !== "Normal" && (
          <div className="anom__ctx" style={{ background: "var(--critical-soft)", color: "var(--critical)" }}>
            <Icon name="alert" size={15} />
            <span>Safety state: {op.safety_state}. A hazard is active in this operator's area.</span>
          </div>
        )}
      </div>
    </Card>
  );
}
