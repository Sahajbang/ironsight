import { useState } from "react";

import {
  useChecklist,
  useCompleteChecklist,
  useDashboard,
  useSafetyEvents,
  useSafetyLive,
  useSafetyTimeline,
} from "../api/client";
import { AlertCard } from "../components";
import { Badge, Button, Card, CardSkeleton, Empty, Icon, Stat, severityTone } from "../design";
import { duration, hhmm, sinceLabel, titleCase } from "../lib/format";
import { useApp } from "../state/store";
import "./pages.css";

export function Safety() {
  const { operatorId } = useApp();
  const { data: live, isLoading } = useSafetyLive(operatorId);
  const { data: dash } = useDashboard(operatorId);
  const nextTask = dash?.current_task?.id ?? dash?.tasks.find((t) => t.status !== "Completed")?.id ?? null;
  const { data: checklist } = useChecklist(nextTask, operatorId);
  const { data: timeline } = useSafetyTimeline(operatorId);
  const { data: events } = useSafetyEvents(operatorId);
  const complete = useCompleteChecklist();
  const [ticked, setTicked] = useState<string[]>([]);

  const allTicked = !!checklist && checklist.items.every((i) => ticked.includes(i));

  return (
    <div className="page__grid">
      <div className="col" style={{ gap: "var(--s5)" }}>
        <Card title="Live safety state" icon="shield" data-testid="safety-live">
          {isLoading || !live ? (
            <CardSkeleton rows={4} />
          ) : (
            <div className="col" style={{ gap: "var(--s4)" }}>
              <div className="sumgrid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
                <Stat label="Critical" value={live.counts.critical} tone={live.counts.critical ? "critical" : "neutral"} />
                <Stat label="Warning" value={live.counts.warning} tone={live.counts.warning ? "warning" : "neutral"} />
                <Stat label="Caution" value={live.counts.caution} tone={live.counts.caution ? "caution" : "neutral"} />
                <Stat label="Hazards" value={live.hazards.length} tone={live.hazards.length ? "critical" : "neutral"} />
              </div>

              <div className="livegrid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
                <div className={`livecell livecell--${live.live.seatbelt_status === "Fastened" ? "ok" : "critical"}`}>
                  <span className="label">Seatbelt</span>
                  <strong>{live.live.seatbelt_status}</strong>
                </div>
                <div
                  className={`livecell livecell--${
                    (live.live.proximity_distance_m ?? 99) < 3
                      ? "critical"
                      : (live.live.proximity_distance_m ?? 99) < 6
                        ? "warning"
                        : "ok"
                  }`}
                >
                  <span className="label">Proximity</span>
                  <strong>{live.live.proximity_distance_m ?? "—"} m</strong>
                </div>
                <div className="livecell livecell--neutral">
                  <span className="label">State</span>
                  <strong>{live.live.operating_state}</strong>
                </div>
                <div className="livecell livecell--neutral">
                  <span className="label">Zone</span>
                  <strong>{live.live.zone ?? "—"}</strong>
                </div>
              </div>
            </div>
          )}
        </Card>

        <Card title="Active alerts" icon="alert" data-guide-id="safety-alerts">
          <div className="stack" data-guide-id="safety-alerts">
            {live?.alerts.length === 0 && <Empty icon="check">No safety rules are firing right now.</Empty>}
            {live?.alerts.map((alert) => (
              <AlertCard key={alert.id} alert={alert} expanded />
            ))}
          </div>
        </Card>

        <Card title="Safety event history" icon="list">
          <div className="stack">
            {(events ?? []).length === 0 && <Empty icon="check">No events logged in the last 7 days.</Empty>}
            {(events ?? []).slice(0, 12).map((e) => (
              <div key={e.id} className="row" style={{ gap: "var(--s3)", padding: "8px 0" }}>
                <Badge tone={severityTone(e.severity)}>{e.severity}</Badge>
                <span className="col grow" style={{ gap: 1 }}>
                  <strong style={{ fontSize: "0.85rem", fontWeight: 500 }}>{e.message}</strong>
                  <span className="muted" style={{ fontSize: "0.72rem" }}>
                    {titleCase(e.event_type)} · {sinceLabel(e.triggered_at)}
                    {e.duration_min != null && ` · resolved after ${duration(e.duration_min)}`}
                  </span>
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="col" style={{ gap: "var(--s5)" }}>
        <Card
          title="Pre-operation checklist"
          icon="check"
          action={checklist?.completed ? <Badge tone="ok">Complete</Badge> : <Badge tone="caution">Required</Badge>}
        >
          <div className="col" style={{ gap: "var(--s3)" }} data-guide-id="start-checklist">
            {!checklist && <CardSkeleton rows={4} />}
            {checklist && (
              <>
                <p className="muted" style={{ fontSize: "0.8rem" }}>
                  Generated for {checklist.task_type} on a {checklist.machine_type?.toLowerCase()} in the current
                  site conditions.
                </p>
                <div className="checklist">
                  {checklist.items.map((item) => {
                    const done = checklist.completed || ticked.includes(item);
                    return (
                      <button
                        key={item}
                        className="checkitem"
                        data-done={done}
                        disabled={checklist.completed}
                        onClick={() =>
                          setTicked((t) => (t.includes(item) ? t.filter((x) => x !== item) : [...t, item]))
                        }
                      >
                        <span className="checkitem__box">
                          <Icon name="check" size={13} />
                        </span>
                        <span>{item}</span>
                      </button>
                    );
                  })}
                </div>
                {!checklist.completed && (
                  <Button
                    variant="primary"
                    block
                    icon="check"
                    disabled={!allTicked || complete.isPending}
                    onClick={() =>
                      complete.mutate({ taskId: checklist.task_id, operatorId, items: checklist.items })
                    }
                  >
                    {allTicked ? "Confirm completion" : `${ticked.length}/${checklist.items.length} checked`}
                  </Button>
                )}
              </>
            )}
          </div>
        </Card>

        <Card title="Shift timeline" icon="clock">
          <div className="timeline" data-guide-id="safety-timeline">
            {(timeline?.entries ?? []).length === 0 && <Empty icon="clock">No safety events this shift.</Empty>}
            {(timeline?.entries ?? []).map((entry, i) => (
              <div key={i} className="tl__row">
                <span className={`tl__dot tl__dot--${entry.kind === "resolved" ? "ok" : severityTone(entry.severity)}`} />
                <span className="tl__time">{hhmm(entry.at)}</span>
                <span className="tl__label">{entry.label}</span>
              </div>
            ))}
          </div>
        </Card>

        {live && live.hazards.length > 0 && (
          <Card title="Active hazards" icon="alert">
            <div className="stack">
              {live.hazards.map((h) => (
                <div key={h.id} className="row" style={{ gap: "var(--s3)" }}>
                  <Badge tone={severityTone(h.severity)}>{h.severity}</Badge>
                  <span className="col grow" style={{ gap: 1 }}>
                    <strong style={{ fontSize: "0.84rem", fontWeight: 500 }}>{h.message}</strong>
                    <span className="muted" style={{ fontSize: "0.72rem" }}>
                      {h.id} · {h.zone} · {sinceLabel(h.created_at)}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
