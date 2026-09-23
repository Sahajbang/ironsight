import type { Alert, Eta, Task } from "../api/client";
import { Badge, Icon, Meter, severityTone } from "../design";
import { duration, hhmm, STATUS_TONE, titleCase } from "../lib/format";
import "./cards.css";

/* ---------------- ETA ---------------- */

/** A range with its drivers, never a bare number — the spread is the honest part of the
 *  prediction and the factors are what let an operator argue with it. */
export function EtaBlock({ eta, compact }: { eta: Eta; compact?: boolean }) {
  return (
    <div className="eta" data-guide-id="task-eta">
      <div className="eta__head">
        <span className="label">Estimated completion</span>
        <Badge tone={eta.confidence === "High" ? "ok" : eta.confidence === "Medium" ? "caution" : "info"}>
          {eta.confidence} confidence
        </Badge>
      </div>

      <div className="eta__range">
        <span className="eta__num">{Math.round(eta.low_estimate_min)}</span>
        <span className="eta__dash">–</span>
        <span className="eta__num">{Math.round(eta.high_estimate_min)}</span>
        <span className="eta__unit">min</span>
      </div>

      {!compact && eta.top_factors && eta.top_factors.length > 0 && (
        <ul className="eta__factors">
          {eta.top_factors.map((f) => (
            <li key={f.name} title={f.detail}>
              <span className={`eta__arrow eta__arrow--${f.direction}`}>
                {f.direction === "increase" ? "▲" : "▼"}
              </span>
              <span className="grow">{f.name}</span>
              <span className="eta__impact">
                {f.impact_min > 0 ? "+" : ""}
                {f.impact_min.toFixed(1)} min
              </span>
            </li>
          ))}
        </ul>
      )}

      {!compact && eta.baseline_comparison?.historical_median_min != null && (
        <p className="eta__baseline">
          Your recent median for this task is {Math.round(eta.baseline_comparison.historical_median_min)} min
          {eta.baseline_comparison.sample_count ? ` across ${eta.baseline_comparison.sample_count} runs` : ""}.
        </p>
      )}
    </div>
  );
}

/* ---------------- Task ---------------- */

export function TaskCard({
  task,
  onStart,
  onOpen,
  active,
}: {
  task: Task;
  onStart?: (id: string) => void;
  onOpen?: (id: string) => void;
  active?: boolean;
}) {
  const tone = STATUS_TONE[task.status] ?? "neutral";
  const startable = task.status === "Ready" || task.status === "Not Started";

  return (
    <article className={`tcard ${active ? "tcard--active" : ""}`} onClick={() => onOpen?.(task.id)}>
      <span className="tcard__time">
        <strong>{hhmm(task.planned_start)}</strong>
        <span>{duration(task.estimated_duration_min)}</span>
      </span>

      <div className="tcard__body">
        <div className="row wrap" style={{ gap: 8 }}>
          <h3 className="tcard__title">{task.task_type}</h3>
          <Badge tone={tone}>{task.status}</Badge>
          {task.priority === "High" && <Badge tone="warning">High priority</Badge>}
        </div>

        <div className="tcard__meta">
          <span>
            <Icon name="map" size={13} /> {task.zone}
          </span>
          <span>
            <Icon name="excavator" size={13} /> {task.machine_id}
          </span>
          {task.eta && (
            <span>
              <Icon name="clock" size={13} /> AI {Math.round(task.eta.low_estimate_min)}–
              {Math.round(task.eta.high_estimate_min)} min
            </span>
          )}
        </div>

        {task.safety_requirements && (
          <span className="tcard__req">
            <Icon name="shield" size={13} />
            {task.safety_requirements}
          </span>
        )}

        {task.status === "In Progress" && (
          <div className="tcard__progress">
            <Meter value={task.progress_pct} />
            <span>{Math.round(task.progress_pct)}%</span>
          </div>
        )}
      </div>

      {startable && onStart && (
        <button
          className="tcard__go"
          onClick={(e) => {
            e.stopPropagation();
            onStart(task.id);
          }}
        >
          <Icon name="play" size={13} />
          Start
        </button>
      )}
    </article>
  );
}

/* ---------------- Alert ---------------- */

/** Every alert answers the five questions from the safety spec. The operator has to be
 *  able to see what fired it, otherwise alerts become noise they learn to dismiss. */
export function AlertCard({ alert, expanded }: { alert: Alert; expanded?: boolean }) {
  const tone = severityTone(alert.severity);
  return (
    <article className={`alert alert--${tone}`}>
      <span className="alert__icon">
        <Icon name={alert.severity === "Critical" ? "alert" : alert.severity === "Warning" ? "alert" : "info"} size={18} />
      </span>

      <div className="grow col" style={{ gap: 6 }}>
        <div className="row wrap" style={{ gap: 8 }}>
          <Badge tone={tone}>{alert.severity}</Badge>
          <span className="alert__type">{titleCase(alert.event_type)}</span>
          {alert.duration_min != null && <span className="alert__age">for {duration(alert.duration_min)}</span>}
        </div>

        <strong className="alert__msg">{alert.message}</strong>

        {expanded && (
          <>
            <p className="alert__reason">{alert.reason}</p>
            <p className="alert__action">
              <Icon name="check" size={13} />
              {alert.recommended_action}
            </p>
            <code className="alert__source">{alert.source_data}</code>
          </>
        )}
      </div>
    </article>
  );
}
