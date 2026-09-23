import { useState } from "react";

import { useAnomalies, useAnomalyFeedback, useEtaAccuracy, usePerformance } from "../api/client";
import { Badge, Button, Card, CardSkeleton, Empty, Icon, Stat } from "../design";
import { duration, sinceLabel, titleCase } from "../lib/format";
import { useApp } from "../state/store";
import "./pages.css";

const CONTEXT_LABEL: Record<string, string> = {
  excessive_idle: "Extended idle period with no recorded dependency.",
  truck_wait: "Truck availability delay recorded during this task.",
};

/** Seeded rows store the raw context key while freshly detected ones already carry a full
 *  sentence — humanising here covers both without needing a data migration. */
const contextText = (value: string) => CONTEXT_LABEL[value] ?? value;

export function Insights() {
  const { operatorId } = useApp();
  const { data: anomalies, isLoading } = useAnomalies(operatorId);
  const { data: perf } = usePerformance(operatorId);
  const { data: accuracy } = useEtaAccuracy();
  const feedback = useAnomalyFeedback();
  const [reasonFor, setReasonFor] = useState<number | null>(null);
  const [reason, setReason] = useState("");

  const maxDuration = Math.max(1, ...(perf?.by_task_type ?? []).map((t) => t.median_duration_min));

  return (
    <div className="page__grid">
      <div className="col" style={{ gap: "var(--s5)" }}>
        <Card title="Unusual operating patterns" icon="target">
          {/* Not "anomaly detected" — the comparison that produced the flag, in the
              operator's own baseline, so they can agree or push back with context. */}
          <div className="stack" data-guide-id="anomaly-list">
            {isLoading && <CardSkeleton rows={4} />}
            {anomalies?.length === 0 && (
              <Empty icon="check">Nothing unusual against your own baselines right now.</Empty>
            )}
            {anomalies?.map((a) => (
              <article key={a.id} className="anom">
                <div className="row wrap" style={{ gap: "var(--s2)" }}>
                  <Badge tone={a.deviation_score >= 2.5 ? "warning" : "caution"}>
                    {a.deviation_score.toFixed(1)}× baseline
                  </Badge>
                  <strong style={{ fontSize: "0.94rem" }}>{titleCase(a.dimension)}</strong>
                  {a.task_type && <span className="muted" style={{ fontSize: "0.78rem" }}>{a.task_type}</span>}
                  <span className="muted" style={{ fontSize: "0.72rem", marginLeft: "auto" }}>
                    {sinceLabel(a.created_at)}
                  </span>
                </div>

                <p style={{ fontSize: "0.9rem", lineHeight: 1.55 }}>{a.explanation}</p>

                <div className="anom__nums">
                  <div className="anom__cell">
                    <span className="label">Actual</span>
                    <strong style={{ fontSize: "1.05rem" }}>{a.actual_value}</strong>
                  </div>
                  <div className="anom__cell">
                    <span className="label">Your typical</span>
                    <strong style={{ fontSize: "1.05rem" }}>{a.baseline_value}</strong>
                  </div>
                  <div className="anom__cell">
                    <span className="label">Status</span>
                    <strong style={{ fontSize: "0.9rem" }}>{a.status}</strong>
                  </div>
                </div>

                {a.possible_context && (
                  <div className="anom__ctx">
                    <Icon name="info" size={15} />
                    <span>Possible context — {contextText(a.possible_context)}</span>
                  </div>
                )}

                {a.feedback_reason && (
                  <div className="anom__ctx" style={{ background: "var(--ok-soft)", color: "var(--ok)" }}>
                    <Icon name="check" size={15} />
                    <span>You said: {a.feedback_reason}</span>
                  </div>
                )}

                {a.status === "Detected" && (
                  <div className="col" style={{ gap: "var(--s2)" }} data-guide-id="anomaly-feedback">
                    <div className="row wrap" style={{ gap: "var(--s2)" }}>
                      <Button
                        size="sm"
                        icon="check"
                        disabled={feedback.isPending}
                        onClick={() =>
                          feedback.mutate({ id: a.id, status: "Confirmed Normal", reason: "Expected for this task." })
                        }
                      >
                        This was normal
                      </Button>
                      <Button size="sm" icon="chat" onClick={() => setReasonFor(reasonFor === a.id ? null : a.id)}>
                        Give the reason
                      </Button>
                    </div>

                    {reasonFor === a.id && (
                      <div className="row" style={{ gap: "var(--s2)" }}>
                        <div className="input grow">
                          <input
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="e.g. waiting on haul truck"
                            aria-label="Reason"
                          />
                        </div>
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={!reason.trim()}
                          onClick={() => {
                            feedback.mutate({ id: a.id, status: "Confirmed Normal", reason: reason.trim() });
                            setReason("");
                            setReasonFor(null);
                          }}
                        >
                          Save
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </article>
            ))}
          </div>
        </Card>

        <Card title="Duration by task type" icon="chart">
          {perf?.by_task_type.length ? (
            <div className="bars">
              {perf.by_task_type.map((t) => (
                <div key={t.task_type} className="bars__col">
                  <span style={{ fontSize: "0.72rem", fontWeight: 700 }}>{Math.round(t.median_duration_min)}</span>
                  <div
                    className="bars__bar bars__bar--accent"
                    style={{ height: `${(t.median_duration_min / maxDuration) * 100}%` }}
                  />
                  <span className="bars__label">{t.task_type}</span>
                </div>
              ))}
            </div>
          ) : (
            <Empty icon="chart">No completed sessions in this window.</Empty>
          )}
        </Card>
      </div>

      <div className="col" style={{ gap: "var(--s5)" }}>
        <Card title="Your performance" icon="gauge">
          {perf ? (
            <div className="col" style={{ gap: "var(--s4)" }}>
              <div className="sumgrid">
                <Stat label="Sessions" value={perf.sessions} />
                <Stat label="On task" value={duration(perf.total_time_min)} />
                <Stat label="Idle" value={duration(perf.idle_time_min)} />
                <Stat
                  label="Idle share"
                  value={perf.idle_share != null ? `${Math.round(perf.idle_share * 100)}%` : "—"}
                  tone={perf.idle_share != null && perf.idle_share > 0.3 ? "caution" : "ok"}
                />
                <Stat label="Load cycles" value={perf.load_cycles} />
                <Stat label="Fuel" value={Math.round(perf.fuel_used_l)} unit="L" />
              </div>
              <p className="muted" style={{ fontSize: "0.76rem" }}>
                Last {perf.window_days} days. These are your own baselines — they are what anomaly detection
                compares against, not a league table.
              </p>
            </div>
          ) : (
            <CardSkeleton rows={4} />
          )}
        </Card>

        <Card title="ETA accuracy" icon="clock">
          {accuracy ? (
            <div className="col" style={{ gap: "var(--s4)" }}>
              <div className="sumgrid">
                <Stat label="Scored" value={accuracy.scored} />
                <Stat label="Mean error" value={accuracy.mae_min != null ? accuracy.mae_min.toFixed(1) : "—"} unit="min" />
                <Stat label="RMSE" value={accuracy.rmse_min != null ? accuracy.rmse_min.toFixed(1) : "—"} unit="min" />
                <Stat
                  label="In range"
                  value={accuracy.interval_coverage != null ? `${Math.round(accuracy.interval_coverage * 100)}%` : "—"}
                  tone={accuracy.interval_coverage != null && accuracy.interval_coverage > 0.6 ? "ok" : "caution"}
                />
              </div>
              <div className="stack">
                {accuracy.entries.slice(0, 5).map((e) => (
                  <div key={e.task_id} className="row" style={{ gap: "var(--s3)", fontSize: "0.78rem" }}>
                    <Icon
                      name={e.within_range ? "check" : "alert"}
                      size={14}
                      style={{ color: e.within_range ? "var(--ok)" : "var(--warning)" }}
                    />
                    <span className="grow muted">{e.task_id}</span>
                    <span>
                      {Math.round(e.predicted_min)} → <strong>{Math.round(e.actual_min)}</strong> min
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <CardSkeleton rows={4} />
          )}
        </Card>
      </div>
    </div>
  );
}
