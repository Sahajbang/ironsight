import { useState } from "react";

import { useCreateIncident, useDashboard, useIncidents, useUpdateIncidentStatus } from "../api/client";
import { Badge, Button, Card, Empty, Icon } from "../design";
import { dayTime, sinceLabel } from "../lib/format";
import { useApp } from "../state/store";
import "./pages.css";

const CATEGORIES = ["Near Miss", "Proximity", "Seatbelt", "Equipment Damage", "Other"];
const SEVERITIES = ["Low", "Medium", "High"];
const FLOW = ["Reported", "Acknowledged", "Under Investigation", "Resolved"];

export function Incidents() {
  const { operatorId } = useApp();
  const { data: dash } = useDashboard(operatorId);
  const { data: incidents } = useIncidents();
  const create = useCreateIncident();
  const updateStatus = useUpdateIncidentStatus();

  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [severity, setSeverity] = useState("Medium");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");

  const zone = dash?.current_task?.zone ?? dash?.tasks[0]?.zone ?? "Zone A";

  function submit() {
    create.mutate(
      {
        operator_id: operatorId,
        category,
        severity,
        description: description.trim(),
        location: location.trim() || zone,
      },
      {
        onSuccess: () => {
          setDescription("");
          setLocation("");
          setOpen(false);
        },
      },
    );
  }

  return (
    <div className="page__grid">
      <div className="col" style={{ gap: "var(--s5)" }}>
        <Card
          title="Incident log"
          icon="alert"
          action={
            /* The guide points at this button and stops. Opening the form is the operator's
               action, and submitting is theirs alone — the assistant has no tool for it. */
            <Button variant="primary" icon="plus" data-guide-id="report-incident" onClick={() => setOpen((o) => !o)}>
              Report incident
            </Button>
          }
        >
          {open && (
            <div className="col" style={{ gap: "var(--s4)", marginBottom: "var(--s5)" }} data-guide-id="incident-form">
              <div className="page__cols">
                <label className="field">
                  <span className="label">Category</span>
                  <select value={category} onChange={(e) => setCategory(e.target.value)}>
                    {CATEGORIES.map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span className="label">Severity</span>
                  <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
                    {SEVERITIES.map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span className="label">Location</span>
                  <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder={zone} />
                </label>
              </div>

              <label className="field">
                <span className="label">What happened?</span>
                <div className="input" style={{ minHeight: 92, alignItems: "flex-start", paddingTop: 12 }}>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                    placeholder="Describe what happened, who was involved and what you did."
                  />
                </div>
              </label>

              <p className="muted" style={{ fontSize: "0.76rem" }}>
                Machine, task and timestamp are attached automatically from your current context.
              </p>

              <div className="row">
                <Button
                  variant="primary"
                  icon="send"
                  data-guide-id="incident-submit"
                  disabled={description.trim().length < 3 || create.isPending}
                  onClick={submit}
                >
                  Submit report
                </Button>
                <Button onClick={() => setOpen(false)}>Cancel</Button>
              </div>
            </div>
          )}

          <div className="stack" data-guide-id="incident-list">
            {(incidents ?? []).length === 0 && <Empty icon="check">No incidents logged.</Empty>}
            {(incidents ?? []).map((incident) => (
              <article key={incident.id} className="anom" style={{ gap: "var(--s3)" }}>
                <div className="row wrap" style={{ gap: "var(--s2)" }}>
                  <Badge tone={incident.severity === "High" ? "critical" : incident.severity === "Medium" ? "warning" : "info"}>
                    {incident.severity}
                  </Badge>
                  <strong style={{ fontSize: "0.92rem" }}>{incident.category}</strong>
                  <span className="muted" style={{ fontSize: "0.75rem" }}>
                    {incident.location} · {sinceLabel(incident.created_at)}
                  </span>
                </div>

                <p style={{ fontSize: "0.86rem", lineHeight: 1.55 }}>{incident.description}</p>

                <div className="row wrap" style={{ justifyContent: "space-between" }}>
                  <div className="flow">
                    {FLOW.map((stage, i) => (
                      <span
                        key={stage}
                        className="flow__step"
                        data-current={stage === incident.status}
                        data-done={i < FLOW.indexOf(incident.status)}
                      >
                        {stage}
                      </span>
                    ))}
                  </div>
                  {incident.next_status && (
                    <Button
                      size="sm"
                      icon="chevronRight"
                      disabled={updateStatus.isPending}
                      onClick={() => updateStatus.mutate({ id: incident.id, status: incident.next_status! })}
                    >
                      {incident.next_status}
                    </Button>
                  )}
                </div>

                <span className="muted" style={{ fontSize: "0.7rem" }}>
                  <Icon name="clock" size={11} style={{ display: "inline", verticalAlign: "-1px" }} /> Reported{" "}
                  {dayTime(incident.created_at)}
                  {incident.machine_id ? ` · ${incident.machine_id}` : ""}
                  {incident.task_id ? ` · ${incident.task_id}` : ""}
                </span>
              </article>
            ))}
          </div>
        </Card>
      </div>

      <Card title="Reporting guidance" icon="info">
        <div className="stack">
          <p style={{ fontSize: "0.85rem", lineHeight: 1.6 }}>
            Log anything that could have caused harm, even when nothing did. A near miss recorded today is
            the cheapest possible warning.
          </p>
          <ul className="stack" style={{ gap: "var(--s2)" }}>
            {[
              "Report as soon as the machine is safe — not at the end of shift.",
              "Say what you saw, not who you blame.",
              "Include the zone; it links the report to the site map.",
              "Critical hazards go to your supervisor by radio first.",
            ].map((tip) => (
              <li key={tip} className="row" style={{ gap: 8, alignItems: "flex-start" }}>
                <Icon name="check" size={14} style={{ marginTop: 4, color: "var(--ok)" }} />
                <span style={{ fontSize: "0.82rem", lineHeight: 1.5 }}>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      </Card>
    </div>
  );
}
