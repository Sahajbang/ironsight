import { useState } from "react";

import { useCompleteTask, useDashboard, useStartTask, useTask } from "../api/client";
import { EtaBlock, TaskCard } from "../components";
import { Badge, Button, Card, CardSkeleton, Empty, Icon, Meter } from "../design";
import { duration, hhmm, pct } from "../lib/format";
import { useApp } from "../state/store";
import "./pages.css";

export function Tasks() {
  const { operatorId } = useApp();
  const { data: dash } = useDashboard(operatorId);
  const [selected, setSelected] = useState<string | null>(null);
  const activeId = selected ?? dash?.current_task?.id ?? dash?.tasks[0]?.id ?? null;
  const { data: task } = useTask(activeId);
  const startTask = useStartTask();
  const completeTask = useCompleteTask();

  return (
    <div className="page__grid">
      <Card title={`Today · ${dash?.tasks.length ?? 0} tasks`} icon="list">
        <div className="stack" data-guide-id="task-timeline">
          {!dash && <CardSkeleton rows={6} />}
          {dash?.tasks.length === 0 && <Empty icon="calendar">Nothing scheduled for this shift.</Empty>}
          {dash?.tasks.map((t) => (
            <TaskCard
              key={t.id}
              task={t}
              active={t.id === activeId}
              onOpen={setSelected}
              onStart={(id) => startTask.mutate(id)}
            />
          ))}
        </div>
      </Card>

      <div className="col" style={{ gap: "var(--s5)" }}>
        {!task ? (
          <Card title="Task detail" icon="info">
            <Empty icon="list">Select a task to see its detail.</Empty>
          </Card>
        ) : (
          <>
            <Card
              title="Task detail"
              icon="info"
              action={<Badge tone={task.status === "In Progress" ? "accent" : "neutral"}>{task.status}</Badge>}
            >
              <div className="col" style={{ gap: "var(--s4)" }}>
                <div className="col" style={{ gap: 2 }}>
                  <h2 style={{ fontSize: "1.18rem" }}>{task.task_type}</h2>
                  <span className="muted" style={{ fontSize: "0.8rem" }}>
                    {task.zone} · {task.machine?.model ?? task.machine_id} · planned {hhmm(task.planned_start)}
                  </span>
                </div>

                <div className="sumgrid">
                  <div className="col" style={{ gap: 2 }}>
                    <span className="label">Planned</span>
                    <strong>{duration(task.estimated_duration_min)}</strong>
                  </div>
                  <div className="col" style={{ gap: 2 }}>
                    <span className="label">Priority</span>
                    <strong>{task.priority}</strong>
                  </div>
                </div>

                {task.status === "In Progress" && (
                  <div className="col" style={{ gap: 6 }}>
                    <div className="row" style={{ justifyContent: "space-between" }}>
                      <span className="label">Progress</span>
                      <span style={{ fontSize: "0.8rem", fontWeight: 700 }}>{pct(task.progress_pct)}</span>
                    </div>
                    <Meter value={task.progress_pct} />
                  </div>
                )}

                {task.eta && <EtaBlock eta={task.eta} />}

                <div className="row wrap" style={{ gap: "var(--s2)" }}>
                  {task.status !== "In Progress" && task.status !== "Completed" && (
                    <Button variant="primary" icon="play" onClick={() => startTask.mutate(task.id)}>
                      Start task
                    </Button>
                  )}
                  {task.status === "In Progress" && (
                    <Button
                      variant="primary"
                      icon="check"
                      onClick={() => completeTask.mutate({ taskId: task.id })}
                      disabled={completeTask.isPending}
                    >
                      Complete task
                    </Button>
                  )}
                </div>

                {completeTask.data?.eta_outcome && completeTask.variables?.taskId === task.id && (
                  <div className="anom__ctx" style={{ background: "var(--ok-soft)", color: "var(--ok)" }}>
                    <Icon name="check" size={15} />
                    <span>
                      Predicted {Math.round(completeTask.data.eta_outcome.predicted_min)} min, actual{" "}
                      {Math.round(completeTask.data.eta_outcome.actual_min)} min (
                      {completeTask.data.eta_outcome.error_min > 0 ? "+" : ""}
                      {completeTask.data.eta_outcome.error_min} min).{" "}
                      {completeTask.data.eta_outcome.within_range
                        ? "Inside the predicted range — the model gets this one as a win."
                        : "Outside the range — stored as training data for the next prediction."}
                    </span>
                  </div>
                )}
              </div>
            </Card>

            <Card
              title="Pre-operation checklist"
              icon="check"
              action={task.checklist_completed ? <Badge tone="ok">Complete</Badge> : <Badge tone="caution">Open</Badge>}
            >
              <div className="checklist">
                {task.checklist.map((item) => (
                  <div key={item} className="checkitem" data-done={task.checklist_completed}>
                    <span className="checkitem__box">
                      <Icon name="check" size={13} />
                    </span>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
