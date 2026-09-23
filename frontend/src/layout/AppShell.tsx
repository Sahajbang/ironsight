import { NavLink, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { useDashboard, useOperators } from "../api/client";
import { Icon, type IconName } from "../design";
import { useApp } from "../state/store";
import { GlobalSearch } from "./GlobalSearch";
import "./shell.css";

/* Nav entries own the `nav-*` ids and page content owns the content ids. They used to
   share them, and since the guide resolves a target with querySelector it always found the
   nav item first — so "show me the active alerts" pointed at the sidebar instead. */
const NAV: { to: string; label: string; icon: IconName; guideId: string }[] = [
  { to: "/", label: "Dashboard", icon: "gauge", guideId: "nav-dashboard" },
  { to: "/site", label: "Live Site", icon: "map", guideId: "nav-site" },
  { to: "/tasks", label: "Tasks", icon: "list", guideId: "nav-tasks" },
  { to: "/safety", label: "Safety", icon: "shield", guideId: "nav-safety" },
  { to: "/training", label: "Training", icon: "book", guideId: "nav-training" },
  { to: "/insights", label: "Insights", icon: "chart", guideId: "nav-insights" },
  { to: "/estimator", label: "Estimator", icon: "clock", guideId: "nav-estimator" },
  { to: "/incidents", label: "Incidents", icon: "alert", guideId: "nav-incidents" },
];

const TITLES: Record<string, string> = {
  "/": "Shift Dashboard",
  "/site": "Live Site Map",
  "/tasks": "Tasks",
  "/safety": "Safety Centre",
  "/training": "Training Hub",
  "/insights": "Operator Insights",
  "/estimator": "Task Estimator",
  "/incidents": "Incidents",
};

export function AppShell({ children }: { children: ReactNode }) {
  const { operatorId, setOperatorId } = useApp();
  const { data: operators } = useOperators();
  const { data } = useDashboard(operatorId);
  const location = useLocation();

  const env = data?.shift.environment;
  const alertCount = data?.safety.alert_count ?? 0;
  const highest = data?.safety.highest_severity ?? "Normal";

  return (
    <div className="shell">
      <nav className="shell__nav" aria-label="Main">
        <div className="brand">
          <span className="brand__mark">
            <Icon name="excavator" size={21} />
          </span>
          <span className="col" style={{ gap: 0 }}>
            <strong className="brand__name">IRONSIGHT</strong>
            <span className="brand__sub">Operator Assistant</span>
          </span>
        </div>

        <ul className="nav">
          {NAV.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to} end={item.to === "/"} className="nav__item" data-guide-id={item.guideId}>
                <Icon name={item.icon} size={19} />
                <span>{item.label}</span>
                {item.to === "/safety" && alertCount > 0 && (
                  <span className={`nav__count nav__count--${highest.toLowerCase()}`}>{alertCount}</span>
                )}
              </NavLink>
            </li>
          ))}
        </ul>

        <div className="nav__foot">
          <span className="label">Signed in as</span>
          <div className="opswitch">
            <Icon name="user" size={16} />
            <select
              value={operatorId}
              onChange={(e) => setOperatorId(e.target.value)}
              aria-label="Switch operator"
            >
              {(operators ?? []).map((op) => (
                <option key={op.id} value={op.id}>
                  {op.name} · {op.skill_level}
                </option>
              ))}
            </select>
            <Icon name="chevronDown" size={14} />
          </div>
        </div>
      </nav>

      <div className="shell__main">
        <header className="topbar">
          <div className="col" style={{ gap: 0 }}>
            <span className="label">{data?.shift.site_id ?? "SITE01"}</span>
            <h1 className="topbar__title">{TITLES[location.pathname] ?? "Ironsight"}</h1>
          </div>

          <GlobalSearch />

          <div className="topbar__meta">
            {env && (
              <span className="chip" title={`${env.weather}, ground ${env.ground_condition.toLowerCase()}`}>
                <Icon name={env.weather === "Rainy" ? "droplet" : env.weather === "Windy" ? "wind" : "bolt"} size={15} />
                {env.weather} · {Math.round(env.temperature_c)}°C
              </span>
            )}
            <span className="chip chip--ok" title="Connectivity">
              <Icon name="wifi" size={15} />
              {data?.shift.connectivity ?? "—"}
            </span>
          </div>
        </header>

        <main className="content">{children}</main>
      </div>
    </div>
  );
}
