import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCompleteTask, useDashboard, useStartTask } from "../api/client";
import { EtaBlock } from "../components";
import {
  Badge,
  Button,
  Card,
  CardSkeleton,
  Empty,
  GaugeTile,
  Icon,
  Knob,
  Meter,
  severityTone,
} from "../design";
import { duration, hhmm, pct, STATUS_TONE } from "../lib/format";
import { useApp } from "../state/store";
import "./pages.css";

/* The dashboard answers four questions at a glance — how far through the shift am I, am I
 * safe, am I working or waiting, when do I finish. Everything else is one tap down inside
 * the tile that owns it, so a glance stays a glance. */
type TileId = "shift" | "safety" | "idle" | "eta";

export function Dashboard() {
  const { operatorId } = useApp();
  const { data, isLoading } = useDashboard(operatorId);
  const startTask = useStartTask();
  const completeTask = useCompleteTask();
  const navigate = useNavigate();
  const [open, setOpen] = useState<TileId | null>(null);

  const toggle = (id: TileId) => setOpen((cur) => (cur === id ? null : id));

  if (isLoading || !data) {
    return (
      <div className="dash">
        <div className="dash__gauges">
          {["", "", "", ""].map((_, i) => (
            <Card key={i}>
              <CardSkeleton rows={2} />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const { shift, tasks, current_task, summary, safety, next_best_actions } = data;
  const live = safety.live;
  const lead = next_best_actions[0];

  const doneRatio = summary.tasks_total ? (summary.tasks_completed / summary.tasks_total) * 100 : 0;
  const idleShare = summary.time_on_task_min ? (summary.idle_time_min / summary.time_on_task_min) * 100 : 0;
  const etaMin = current_task?.eta?.point_estimate_min ?? tasks.find((t) => t.eta)?.eta?.point_estimate_min ?? null;
  const safetyTone = safety.alert_count ? severityTone(safety.highest_severity) : "ok";

  return (
    <div className="dash">
      {/* ---------- four dials ---------- */}
      <div className="dash__gauges">
        <GaugeTile
          label="Shift"
          open={open === "shift"}
          onToggle={() => toggle("shift")}
          footer={`${summary.tasks_completed} of ${summary.tasks_total} done`}
          detail={
            <div className="minigrid">
              <MiniStat label="Remaining" value={String(summary.tasks_remaining)} />
              <MiniStat label="On task" value={duration(summary.time_on_task_min)} />
              <MiniStat label="Finish" value={hhmm(summary.predicted_shift_completion)} />
              <MiniStat label="Started" value={hhmm(shift.shift_start)} />
            </div>
          }
        >
          <Knob value={doneRatio} display={`${summary.tasks_completed}/${summary.tasks_total}`} />
        </GaugeTile>

        <GaugeTile
          label="Safety"
          open={open === "safety"}
          onToggle={() => toggle("safety")}
          footer={safety.alert_count ? safety.highest_severity : "All clear"}
          detail={
            <div className="col" style={{ gap: "var(--s2)" }}>
              {safety.alerts.length === 0 && <span>No rules firing right now.</span>}
              {safety.alerts.slice(0, 3).map((a) => (
                <div key={a.id} className="row" style={{ gap: 8, alignItems: "flex-start" }}>
                  <Badge tone={severityTone(a.severity)}>{a.severity}</Badge>
                  <span className="grow">{a.message}</span>
                </div>
              ))}
              <Button size="sm" icon="shield" onClick={() => navigate("/safety")}>
                Safety centre
              </Button>
            </div>
          }
        >
          <Knob
            value={Math.min(safety.alert_count, 4)}
            max={4}
            display={String(safety.alert_count)}
            tone={safetyTone}
          />
        </GaugeTile>

        <GaugeTile
          label="Idle share"
          open={open === "idle"}
          onToggle={() => toggle("idle")}
          footer={`${duration(summary.idle_time_min)} idle`}
          detail={
            <div className="minigrid">
              <MiniStat label="Idle" value={duration(summary.idle_time_min)} />
              <MiniStat label="Working" value={duration(summary.time_on_task_min)} />
              <MiniStat label="Cycles" value={String(current_task?.progress_pct ? "—" : "—")} />
              <MiniStat label="Incidents" value={String(summary.incidents_logged)} />
            </div>
          }
        >
          <Knob
            value={idleShare}
            display={`${Math.round(idleShare)}`}
            unit="%"
            tone={idleShare > 35 ? "caution" : "ok"}
          />
        </GaugeTile>

        <GaugeTile
          label="Next finish"
          open={open === "eta"}
          onToggle={() => toggle("eta")}
          footer={current_task ? "Current task" : "Next task"}
          detail={
            current_task?.eta ? (
              <EtaBlock eta={current_task.eta} />
            ) : (
              <span>Start a task to get a live predicted finish time.</span>
            )
          }
        >
          <Knob
            value={etaMin ?? 0}
            max={120}
            display={etaMin ? String(Math.round(etaMin)) : "—"}
            unit={etaMin ? "min" : undefined}
          />
        </GaugeTile>
      </div>

      {/* ---------- one recommended action ---------- */}
      {lead && (
        <button className="leadaction" onClick={() => navigate(lead.route)} data-guide-id="next-best-action">
          <span className={`leadaction__mark leadaction__mark--${severityTone(lead.severity)}`}>
            <Icon name="bolt" size={17} />
          </span>
          <span className="col grow" style={{ gap: 1, textAlign: "left" }}>
            <strong className="leadaction__title">{lead.title}</strong>
            <span className="leadaction__why">{lead.reason}</span>
          </span>
          {next_best_actions.length > 1 && (
            <span className="leadaction__more">+{next_best_actions.length - 1} more</span>
          )}
          <Icon name="chevronRight" size={17} />
        </button>
      )}

      {/* ---------- work ---------- */}
      <div className="dash__work">
        <Card
          title={current_task ? "Current task" : "Up next"}
          icon={current_task ? "play" : "clock"}
          action={
            current_task ? (
              <Badge tone="accent">{pct(current_task.progress_pct)}</Badge>
            ) : (
              <Badge tone="neutral">{tasks.filter((t) => t.status !== "Completed").length} to go</Badge>
            )
          }
        >
          {current_task ? (
            <div className="col" style={{ gap: "var(--s4)" }} data-guide-id="current-task">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <div className="col" style={{ gap: 1 }}>
                  <h2 style={{ fontSize: "1.14rem" }}>{current_task.task_type}</h2>
                  <span className="muted" style={{ fontSize: "0.78rem" }}>
                    {current_task.zone} · {current_task.machine_id} · {duration(current_task.elapsed_min)} elapsed
                  </span>
                </div>
              </div>
              <Meter value={current_task.progress_pct} />
              <div className="row wrap" style={{ gap: "var(--s2)" }}>
                <Button
                  variant="primary"
                  icon="check"
                  onClick={() => completeTask.mutate({ taskId: current_task.id })}
                  disabled={completeTask.isPending}
                >
                  Complete
                </Button>
                <Button icon="alert" onClick={() => navigate("/incidents")}>
                  Report
                </Button>
              </div>
            </div>
          ) : (
            <NextUp
              tasks={tasks}
              onStart={(id) => startTask.mutate(id)}
              onOpen={() => navigate("/tasks")}
            />
          )}
        </Card>

        <Card title="Today" icon="list" action={<Badge>{tasks.length}</Badge>}>
          <div className="tline" data-guide-id="task-timeline">
            {tasks.length === 0 && <Empty icon="calendar">Nothing scheduled.</Empty>}
            {tasks.map((task) => (
              <button key={task.id} className="tline__row" onClick={() => navigate("/tasks")}>
                <span className="tline__time">{hhmm(task.planned_start)}</span>
                <span className={`tline__dot tline__dot--${STATUS_TONE[task.status] ?? "neutral"}`} />
                <span className="grow col" style={{ gap: 0, textAlign: "left" }}>
                  <strong className="tline__name">{task.task_type}</strong>
                  <span className="tline__meta">
                    {task.zone} · {duration(task.estimated_duration_min)}
                    {task.safety_requirements ? " · checklist" : ""}
                  </span>
                </span>
                {(task.status === "Ready" || task.status === "Not Started") && (
                  <span
                    className="tline__go"
                    role="button"
                    tabIndex={0}
                    onClick={(e) => {
                      e.stopPropagation();
                      startTask.mutate(task.id);
                    }}
                    onKeyDown={(e) => e.key === "Enter" && startTask.mutate(task.id)}
                  >
                    <Icon name="play" size={12} />
                  </span>
                )}
              </button>
            ))}
          </div>
        </Card>

        <div className="dash__strip">
          <MiniTile label="Machine" value={shift.machine?.model ?? "—"} sub={shift.machine?.id ?? ""} icon="excavator" />
          <MiniTile
            label="Seatbelt"
            value={live.seatbelt_status}
            tone={live.seatbelt_status === "Fastened" ? "ok" : "critical"}
            icon="shield"
          />
          <MiniTile
            label="Proximity"
            value={live.proximity_distance_m != null ? `${live.proximity_distance_m} m` : "—"}
            tone={
              live.proximity_distance_m == null
                ? undefined
                : live.proximity_distance_m < 3
                  ? "critical"
                  : live.proximity_distance_m < 6
                    ? "warning"
                    : "ok"
            }
            icon="target"
          />
          <MiniTile label="State" value={live.operating_state} sub={live.zone ?? ""} icon="gauge" />
          <MiniTile
            label="Weather"
            value={shift.environment?.weather ?? "—"}
            sub={shift.environment ? `${Math.round(shift.environment.temperature_c)}°C` : ""}
            icon="wind"
          />
        </div>
      </div>
    </div>
  );
}

function NextUp({
  tasks,
  onStart,
  onOpen,
}: {
  tasks: { id: string; task_type: string; zone: string; planned_start: string; estimated_duration_min: number; status: string; safety_requirements: string | null }[];
  onStart: (id: string) => void;
  onOpen: () => void;
}) {
  const next = tasks.find((t) => t.status === "Ready") ?? tasks.find((t) => t.status !== "Completed");
  if (!next) return <Empty icon="check">Shift complete.</Empty>;
  return (
    <div className="col" style={{ gap: "var(--s4)" }}>
      <div className="col" style={{ gap: 1 }}>
        <h2 style={{ fontSize: "1.14rem" }}>{next.task_type}</h2>
        <span className="muted" style={{ fontSize: "0.78rem" }}>
          {hhmm(next.planned_start)} · {next.zone} · {duration(next.estimated_duration_min)}
        </span>
      </div>
      {next.safety_requirements && (
        <span className="tcard__req">
          <Icon name="shield" size={13} />
          {next.safety_requirements}
        </span>
      )}
      <div className="row wrap" style={{ gap: "var(--s2)" }}>
        <Button variant="primary" icon="play" onClick={() => onStart(next.id)}>
          Start
        </Button>
        <Button icon="list" onClick={onOpen}>
          Details
        </Button>
      </div>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="col" style={{ gap: 0 }}>
      <span className="label">{label}</span>
      <strong style={{ fontSize: "0.92rem" }}>{value}</strong>
    </div>
  );
}

function MiniTile({
  label,
  value,
  sub,
  tone,
  icon,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "ok" | "warning" | "critical";
  icon: "excavator" | "shield" | "target" | "gauge" | "wind";
}) {
  return (
    <div className={`mtile ${tone ? `mtile--${tone}` : ""}`}>
      <Icon name={icon} size={16} />
      <span className="label">{label}</span>
      <strong className="mtile__value">{value}</strong>
      {sub && <span className="mtile__sub">{sub}</span>}
    </div>
  );
}
