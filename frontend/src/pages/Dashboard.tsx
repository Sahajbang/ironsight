import { useNavigate } from "react-router-dom";

import { useCompleteTask, useDashboard, useStartTask } from "../api/client";
import { AlertCard, EtaBlock, TaskCard } from "../components";
import { Badge, Button, Card, CardSkeleton, Empty, Icon, Meter, Stat, severityTone } from "../design";
import { duration, hhmm, pct } from "../lib/format";
import { useApp } from "../state/store";
import "./pages.css";

export function Dashboard() {
  const { operatorId } = useApp();
  const { data, isLoading } = useDashboard(operatorId);
  const startTask = useStartTask();
  const completeTask = useCompleteTask();
  const navigate = useNavigate();

  if (isLoading || !data) {
    return (
      <div className="dash">
        <Card className="dash__full">
          <CardSkeleton rows={2} />
        </Card>
        <Card>
          <CardSkeleton rows={5} />
        </Card>
        <Card>
          <CardSkeleton rows={4} />
        </Card>
      </div>
    );
  }

  const { shift, tasks, current_task, summary, safety, next_best_actions } = data;
  const live = safety.live;

  return (
    <div className="dash">
      {/* ---------- next best action ---------- */}
      <Card className="dash__full" title="Next best action" icon="target" variant="tight">
        <div className="nba" data-guide-id="next-best-action">
          {next_best_actions.length === 0 && <Empty icon="check">Nothing needs your attention right now.</Empty>}
          {next_best_actions.map((action, i) => (
            <button
              key={action.id}
              className={`nba__item ${i === 0 ? "nba__item--lead" : ""}`}
              onClick={() => navigate(action.route)}
            >
              <span className={`nba__mark nba__mark--${severityTone(action.severity)}`}>
                <Icon name={i === 0 ? "bolt" : "chevronRight"} size={16} />
              </span>
              <span className="col grow" style={{ gap: 2 }}>
                <strong className="nba__title">{action.title}</strong>
                <span className="nba__reason">{action.reason}</span>
                <code className="nba__source">{action.source}</code>
              </span>
              <Icon name="chevronRight" size={16} />
            </button>
          ))}
        </div>
      </Card>

      {/* ---------- main column ---------- */}
      <div className="col" style={{ gap: "var(--s5)" }}>
        {current_task ? (
          <Card title="Current task" icon="play">
            <div className="cur" data-guide-id="current-task">
              <div className="cur__head">
                <div className="col" style={{ gap: 2 }}>
                  <h2 className="cur__title">{current_task.objective}</h2>
                  <span className="muted" style={{ fontSize: "0.8rem" }}>
                    Started {hhmm(current_task.planned_start)} · {current_task.machine_id}
                  </span>
                </div>
                <Badge tone="accent">In progress</Badge>
              </div>

              <div className="cur__grid">
                <Stat label="Elapsed" value={duration(current_task.elapsed_min)} />
                <Stat label="Progress" value={pct(current_task.progress_pct)} />
                <Stat label="Planned" value={duration(current_task.estimated_duration_min)} />
              </div>

              <Meter value={current_task.progress_pct} />

              {current_task.eta && <EtaBlock eta={current_task.eta} />}

              {current_task.relevant_alerts.length > 0 && (
                <div className="col" style={{ gap: "var(--s2)" }}>
                  {current_task.relevant_alerts.map((a) => (
                    <AlertCard key={a.id} alert={a} />
                  ))}
                </div>
              )}

              <div className="row wrap" style={{ gap: "var(--s2)" }}>
                <Button
                  variant="primary"
                  icon="check"
                  onClick={() => completeTask.mutate({ taskId: current_task.id })}
                  disabled={completeTask.isPending}
                >
                  Complete task
                </Button>
                <Button icon="shield" onClick={() => navigate("/safety")}>
                  Safety
                </Button>
                <Button icon="book" onClick={() => navigate("/training")}>
                  Training
                </Button>
                <Button icon="alert" onClick={() => navigate("/incidents")}>
                  Report incident
                </Button>
              </div>
            </div>
          </Card>
        ) : (
          <Card title="Current task" icon="play">
            <Empty icon="clock">
              No task in progress. Start the next one from your timeline below.
            </Empty>
          </Card>
        )}

        <Card title={`Today · ${tasks.length} tasks`} icon="list">
          <div className="col" style={{ gap: "var(--s3)" }} data-guide-id="task-timeline">
            {tasks.length === 0 && <Empty icon="calendar">Nothing scheduled for this shift.</Empty>}
            {tasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                active={task.status === "In Progress"}
                onStart={(id) => startTask.mutate(id)}
                onOpen={() => navigate("/tasks")}
              />
            ))}
          </div>
        </Card>
      </div>

      {/* ---------- side column ---------- */}
      <div className="col" style={{ gap: "var(--s5)" }}>
        <Card
          title="Safety"
          icon="shield"
          action={
            <Badge tone={safety.alert_count ? severityTone(safety.highest_severity) : "ok"}>
              {safety.alert_count ? `${safety.alert_count} active` : "All clear"}
            </Badge>
          }
        >
          <div className="col" style={{ gap: "var(--s3)" }}>
            <div className="livegrid">
              <LiveCell
                label="Seatbelt"
                value={live.seatbelt_status}
                tone={live.seatbelt_status === "Fastened" ? "ok" : "critical"}
              />
              <LiveCell
                label="Proximity"
                value={live.proximity_distance_m != null ? `${live.proximity_distance_m} m` : "—"}
                tone={
                  live.proximity_distance_m == null
                    ? "neutral"
                    : live.proximity_distance_m < 3
                      ? "critical"
                      : live.proximity_distance_m < 6
                        ? "warning"
                        : "ok"
                }
              />
              <LiveCell label="State" value={live.operating_state} tone="neutral" />
              <LiveCell label="Zone" value={live.zone ?? "—"} tone="neutral" />
            </div>

            {safety.alerts.slice(0, 2).map((a) => (
              <AlertCard key={a.id} alert={a} />
            ))}

            <Button block icon="shield" onClick={() => navigate("/safety")}>
              Open safety centre
            </Button>
          </div>
        </Card>

        <Card title="Shift summary" icon="chart">
          <div className="sumgrid">
            <Stat label="Completed" value={summary.tasks_completed} />
            <Stat label="Remaining" value={summary.tasks_remaining} />
            <Stat label="On task" value={duration(summary.time_on_task_min)} />
            <Stat label="Idle" value={duration(summary.idle_time_min)} />
            <Stat label="Safety events" value={summary.safety_events} tone={summary.safety_events ? "caution" : "ok"} />
            <Stat label="Incidents" value={summary.incidents_logged} />
          </div>
          {summary.predicted_shift_completion && (
            <p className="dash__note">
              <Icon name="clock" size={14} />
              Predicted shift completion {hhmm(summary.predicted_shift_completion)}
            </p>
          )}
        </Card>

        <Card title="Machine" icon="excavator">
          {shift.machine ? (
            <div className="col" style={{ gap: "var(--s3)" }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <div className="col" style={{ gap: 0 }}>
                  <strong style={{ fontSize: "1.02rem" }}>{shift.machine.model}</strong>
                  <span className="muted" style={{ fontSize: "0.78rem" }}>
                    {shift.machine.id} · {shift.machine.machine_type}
                  </span>
                </div>
                <Badge tone={live.engine_on ? "ok" : "neutral"}>{live.engine_on ? "Running" : "Off"}</Badge>
              </div>
              <div className="sumgrid">
                <Stat label="Engine hours" value={Math.round(shift.machine.engine_hours)} />
                <Stat label="Age" value={shift.machine.age_years} unit="yr" />
              </div>
            </div>
          ) : (
            <Empty icon="excavator">No machine assigned.</Empty>
          )}
        </Card>
      </div>
    </div>
  );
}

function LiveCell({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "ok" | "warning" | "critical" | "neutral";
}) {
  return (
    <div className={`livecell livecell--${tone}`}>
      <span className="label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
