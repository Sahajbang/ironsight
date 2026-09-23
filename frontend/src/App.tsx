import { Route, Routes } from "react-router-dom";

import { ChatPanel } from "./chat/ChatPanel";
import { GuideLayer } from "./guide/GuideLayer";
import { AppShell } from "./layout/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { Estimator } from "./pages/Estimator";
import { Incidents } from "./pages/Incidents";
import { Insights } from "./pages/Insights";
import { Safety } from "./pages/Safety";
import { SiteMap } from "./pages/SiteMap";
import { Tasks } from "./pages/Tasks";
import { Training } from "./pages/Training";

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/site" element={<SiteMap />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/safety" element={<Safety />} />
        <Route path="/training" element={<Training />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/estimator" element={<Estimator />} />
        <Route path="/incidents" element={<Incidents />} />
      </Routes>
      <ChatPanel />
      <GuideLayer />
    </AppShell>
  );
}
