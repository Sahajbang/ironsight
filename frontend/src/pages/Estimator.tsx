import { useState } from "react";

import { usePredictEta } from "../api/client";
import { EtaBlock } from "../components";
import { Button, Card, Empty, Icon } from "../design";
import { useApp } from "../state/store";
import "./pages.css";

const TASK_TYPES = ["Earth Excavation", "Trenching", "Material Loading", "Grading", "Demolition"];
const WEATHER = ["Sunny", "Cloudy", "Rainy", "Windy"];
const SKILLS = ["Beginner", "Intermediate", "Expert"];
const PLANNED: Record<string, number> = {
  "Earth Excavation": 60,
  Trenching: 50,
  "Material Loading": 30,
  Grading: 35,
  Demolition: 90,
};

export function Estimator() {
  const { operatorId } = useApp();
  const predict = usePredictEta();
  const [taskType, setTaskType] = useState(TASK_TYPES[1]);
  const [weather, setWeather] = useState("Sunny");
  const [skill, setSkill] = useState("Expert");
  const [machineAge, setMachineAge] = useState(2);
  const [planned, setPlanned] = useState(PLANNED[TASK_TYPES[1]]);

  function run() {
    predict.mutate({
      task_type: taskType,
      estimated_duration_min: planned,
      weather,
      operator_skill: skill,
      machine_age: machineAge,
      operator_id: operatorId,
    });
  }

  return (
    <div className="page__grid">
      <Card title="What-if estimator" icon="clock">
        {/* Changing one input at a time and watching the range move is how an operator
            builds trust in the model — far more convincing than a single number. */}
        <div className="col" style={{ gap: "var(--s4)" }} data-guide-id="task-estimator">
          <div className="page__cols">
            <label className="field">
              <span className="label">Task type</span>
              <select
                value={taskType}
                onChange={(e) => {
                  setTaskType(e.target.value);
                  setPlanned(PLANNED[e.target.value] ?? 45);
                }}
              >
                {TASK_TYPES.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </label>

            <label className="field">
              <span className="label">Weather</span>
              <select value={weather} onChange={(e) => setWeather(e.target.value)}>
                {WEATHER.map((w) => (
                  <option key={w}>{w}</option>
                ))}
              </select>
            </label>

            <label className="field">
              <span className="label">Operator skill</span>
              <select value={skill} onChange={(e) => setSkill(e.target.value)}>
                {SKILLS.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </label>

            <label className="field">
              <span className="label">Machine age (years)</span>
              <input
                type="number"
                min={0}
                max={25}
                value={machineAge}
                onChange={(e) => setMachineAge(Number(e.target.value))}
              />
            </label>

            <label className="field">
              <span className="label">Planned duration (min)</span>
              <input
                type="number"
                min={5}
                max={480}
                value={planned}
                onChange={(e) => setPlanned(Number(e.target.value))}
              />
            </label>
          </div>

          <Button variant="primary" icon="bolt" onClick={run} disabled={predict.isPending}>
            {predict.isPending ? "Predicting…" : "Predict duration"}
          </Button>
        </div>
      </Card>

      <div className="col" style={{ gap: "var(--s5)" }}>
        <Card title="Prediction" icon="target">
          {predict.data ? (
            <EtaBlock eta={predict.data} />
          ) : (
            <Empty icon="clock">Set the conditions and run a prediction.</Empty>
          )}
        </Card>

        {predict.data && (
          <Card title="How this was produced" icon="info">
            <p style={{ fontSize: "0.84rem", lineHeight: 1.6 }}>
              A gradient-boosted model trained on completed sessions predicts the point estimate. The range
              comes from the model's own residual spread, widened when there is little history for this
              operator and task. Each factor above is measured by re-running the prediction with that one
              input reset to typical — so it is the effect for <em>this</em> estimate, not a global average.
            </p>
            <p className="muted" style={{ fontSize: "0.76rem", marginTop: "var(--s3)" }}>
              <Icon name="info" size={12} style={{ display: "inline", verticalAlign: "-2px" }} /> Model:{" "}
              {predict.data.model === "gradient_boosting" ? "gradient boosting" : "rule-based fallback"}
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
