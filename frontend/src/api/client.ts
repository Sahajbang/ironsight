import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

/* Vite proxies /api to the FastAPI process, so everything stays same-origin. */

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${detail ? ` — ${detail.slice(0, 200)}` : ""}`);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

const patch = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "PATCH", body: JSON.stringify(body) });

/* ------------------------------------------------------------------ types */

export interface Operator {
  id: string;
  name: string;
  skill_level: string;
  experience_years: number;
  machine?: Machine | null;
}

export interface Machine {
  id: string;
  machine_type: string;
  model: string;
  age_years: number;
  engine_hours: number;
}

export interface Eta {
  point_estimate_min: number;
  low_estimate_min: number;
  high_estimate_min: number;
  confidence: string;
  top_factors?: { name: string; impact_min: number; direction: string; detail: string }[];
  baseline_comparison?: {
    historical_median_min: number | null;
    sample_count?: number;
    delta_vs_baseline_min?: number | null;
  };
  model?: string;
}

export interface Task {
  id: string;
  operator_id: string;
  machine_id: string;
  zone: string;
  task_type: string;
  priority: string;
  planned_start: string;
  estimated_duration_min: number;
  ai_predicted_duration_min: number | null;
  expected_completion: string;
  status: string;
  dependencies: string | null;
  required_training: string | null;
  safety_requirements: string | null;
  progress_pct: number;
  elapsed_min: number | null;
  eta: Eta | null;
}

export interface Alert {
  id: string;
  event_type: string;
  severity: string;
  message: string;
  reason: string;
  recommended_action: string;
  source_data: string;
  duration_min: number | null;
  triggered_at: string;
}

export interface NextBestAction {
  id: string;
  title: string;
  reason: string;
  source: string;
  severity: string;
  route: string;
  guide_id: string;
}

export interface Dashboard {
  shift: {
    operator: Operator;
    machine: Machine | null;
    site_id: string;
    shift_date: string;
    shift_start: string;
    current_time: string;
    connectivity: string;
    machine_status: string;
    environment: {
      weather: string;
      temperature_c: number;
      wind_kph: number;
      visibility: string;
      ground_condition: string;
    } | null;
  };
  tasks: Task[];
  current_task: (Task & { objective: string; relevant_alerts: Alert[] }) | null;
  summary: {
    tasks_total: number;
    tasks_completed: number;
    tasks_remaining: number;
    time_on_task_min: number;
    idle_time_min: number;
    safety_events: number;
    incidents_logged: number;
    predicted_shift_completion: string | null;
  };
  safety: {
    alert_count: number;
    highest_severity: string;
    alerts: Alert[];
    live: LiveMachine;
  };
  next_best_actions: NextBestAction[];
}

export interface LiveMachine {
  machine_id: string | null;
  seatbelt_status: string;
  proximity_distance_m: number | null;
  engine_on: boolean;
  operating_state: string;
  zone: string | null;
  safety_state: string;
}

export interface SafetyLive {
  operator_id: string;
  generated_at: string;
  live: LiveMachine;
  hazards: Hazard[];
  alerts: Alert[];
  counts: { critical: number; warning: number; caution: number; informational: number };
}

export interface Hazard {
  id: string;
  hazard_type: string;
  severity: string;
  zone: string;
  x: number;
  y: number;
  message: string;
  source: string;
  created_at: string;
  status: string;
  affected_operators: string[];
}

export interface SafetyEvent {
  id: number;
  event_type: string;
  severity: string;
  message: string;
  reason: string;
  recommended_action: string;
  source_data: string;
  triggered_at: string;
  resolved_at: string | null;
  duration_min: number | null;
}

export interface Incident {
  id: number;
  operator_id: string;
  machine_id: string | null;
  task_id: string | null;
  category: string;
  severity: string;
  description: string;
  location: string;
  status: string;
  created_at: string;
  updated_at: string;
  next_status: string | null;
}

export interface TrainingItem {
  id: string;
  title: string;
  content_type: string;
  machine_family: string;
  task_type: string | null;
  skill_level: string;
  duration_min: number | null;
  body_text: string;
  url: string;
  status?: string;
  score?: number | null;
  completed_at?: string | null;
}

export interface TrainingRecommendation {
  content: TrainingItem;
  reason: string;
  trigger: string;
  priority: number;
}

export interface InstructorSlot {
  id: number;
  instructor_name: string;
  expertise: string;
  topic: string;
  mode: string;
  location: string | null;
  start_time: string;
  end_time: string;
  booked: boolean;
  booked_by_operator_id: string | null;
}

export interface SearchResult extends TrainingItem {
  result_type: string;
  score: number;
  context_reasons: string[];
  snippet: string;
}

export interface SearchResponse {
  query: string;
  total: number;
  quick_answer: { text: string; source_id: string; source_title: string; source_url: string } | null;
  results: SearchResult[];
  groups: { type: string; items: SearchResult[] }[];
}

export interface Anomaly {
  id: number;
  task_session_id: number;
  operator_id: string;
  task_id: string | null;
  task_type: string | null;
  dimension: string;
  baseline_value: number;
  actual_value: number;
  deviation_score: number;
  explanation: string;
  possible_context: string | null;
  status: string;
  feedback_reason: string | null;
  created_at: string;
  actions: string[];
}

export interface GuideAction {
  action: "navigate" | "scroll" | "highlight" | "explain" | "tooltip";
  target: string | null;
  route: string | null;
  message: string;
  waitForUser: boolean;
}

export interface AssistantReply {
  reply: string;
  guide_actions: GuideAction[];
  tools_used: string[];
  sources: { id: string; title: string; type: string; url: string }[];
  source: "nemotron" | "fallback";
  model: string | null;
  degraded: boolean;
  degraded_reason?: string;
}

export interface SiteOperator {
  operator_id: string;
  operator_name: string;
  machine_id: string | null;
  machine_type: string | null;
  zone: string;
  x: number;
  y: number;
  heading: number;
  current_task_id: string | null;
  task_status: string;
  operating_state: string;
  workload_score: number;
  safety_state: string;
  seatbelt_status: string;
  proximity_distance_m: number;
  event_type: string;
}

export interface SiteSnapshot {
  site_id: string;
  tick: number;
  generated_at: string;
  zones: { id: string; label: string; x: number; y: number; w: number; h: number; kind: string }[];
  haul_route: [number, number][];
  operators: SiteOperator[];
  hazards: Hazard[];
  recent_events: {
    tick: number;
    timestamp: string;
    operator_id: string;
    zone: string | null;
    event_type: string;
    message: string;
    hazard_id: string | null;
  }[];
}

export interface Performance {
  operator_id: string;
  window_days: number;
  sessions: number;
  total_time_min: number;
  idle_time_min: number;
  idle_share: number | null;
  load_cycles: number;
  fuel_used_l: number;
  eta_accuracy: { predictions_scored: number; mae_min: number | null };
  by_task_type: {
    task_type: string;
    sessions: number;
    median_duration_min: number;
    median_idle_min: number;
  }[];
}

export interface EtaAccuracy {
  scored: number;
  mae_min: number | null;
  rmse_min: number | null;
  interval_coverage: number | null;
  entries: {
    task_id: string;
    predicted_min: number;
    range: [number, number];
    actual_min: number;
    error_min: number;
    within_range: boolean;
    recorded_at: string;
  }[];
}

/* ------------------------------------------------------------------ hooks */

const LIVE = { refetchInterval: 4000 };

export const useOperators = () => useQuery({ queryKey: ["operators"], queryFn: () => request<Operator[]>("/operators") });

export const useDashboard = (operatorId: string) =>
  useQuery({
    queryKey: ["dashboard", operatorId],
    queryFn: () => request<Dashboard>(`/dashboard?operator_id=${operatorId}`),
    ...LIVE,
  });

export const useTask = (taskId: string | null) =>
  useQuery({
    queryKey: ["task", taskId],
    queryFn: () => request<Task & { checklist: string[]; checklist_completed: boolean; machine: Machine }>(`/tasks/${taskId}`),
    enabled: !!taskId,
  });

export const useSafetyLive = (operatorId: string) =>
  useQuery({
    queryKey: ["safety-live", operatorId],
    queryFn: () => request<SafetyLive>(`/safety/live?operator_id=${operatorId}`),
    ...LIVE,
  });

export const useSafetyEvents = (operatorId: string) =>
  useQuery({
    queryKey: ["safety-events", operatorId],
    queryFn: () => request<SafetyEvent[]>(`/safety/events?operator_id=${operatorId}`),
  });

export const useSafetyTimeline = (operatorId: string) =>
  useQuery({
    queryKey: ["safety-timeline", operatorId],
    queryFn: () =>
      request<{ shift_start: string; entries: { at: string; kind: string; event_type: string; severity: string; label: string }[] }>(
        `/safety/timeline?operator_id=${operatorId}`,
      ),
  });

export const useChecklist = (taskId: string | null, operatorId: string) =>
  useQuery({
    queryKey: ["checklist", taskId, operatorId],
    queryFn: () =>
      request<{ task_id: string; task_type: string; machine_type: string; items: string[]; completed: boolean }>(
        `/safety/checklist?operator_id=${operatorId}${taskId ? `&task_id=${taskId}` : ""}`,
      ),
  });

export const useIncidents = (operatorId?: string) =>
  useQuery({
    queryKey: ["incidents", operatorId],
    queryFn: () => request<Incident[]>(`/incidents${operatorId ? `?operator_id=${operatorId}` : ""}`),
  });

export const useTraining = (operatorId: string) =>
  useQuery({
    queryKey: ["training", operatorId],
    queryFn: () =>
      request<{
        total: number;
        items: TrainingItem[];
        categories: { content_type: string; items: TrainingItem[] }[];
        progress: { completed: number; in_progress: number; not_started: number };
      }>(`/training?operator_id=${operatorId}`),
  });

export const useTrainingRecommendations = (operatorId: string) =>
  useQuery({
    queryKey: ["training-recs", operatorId],
    queryFn: () => request<TrainingRecommendation[]>(`/training/recommendations?operator_id=${operatorId}`),
  });

export const useInstructors = () =>
  useQuery({ queryKey: ["instructors"], queryFn: () => request<InstructorSlot[]>("/instructors/availability") });

export const useSearch = (query: string, operatorId: string) =>
  useQuery({
    queryKey: ["search", query, operatorId],
    queryFn: () => request<SearchResponse>(`/search?q=${encodeURIComponent(query)}&operator_id=${operatorId}`),
    enabled: query.trim().length >= 2,
    staleTime: 60_000, // repeated queries come straight from cache — search must feel instant
  });

export const useAnomalies = (operatorId: string) =>
  useQuery({
    queryKey: ["anomalies", operatorId],
    queryFn: () => request<Anomaly[]>(`/insights/anomalies?operator_id=${operatorId}`),
  });

export const usePerformance = (operatorId: string) =>
  useQuery({
    queryKey: ["performance", operatorId],
    queryFn: () => request<Performance>(`/insights/performance?operator_id=${operatorId}`),
  });

export const useEtaAccuracy = () =>
  useQuery({ queryKey: ["eta-accuracy"], queryFn: () => request<EtaAccuracy>("/eta/accuracy") });

export const useSiteMap = (operatorId: string | null, view: "operator" | "supervisor") =>
  useQuery({
    queryKey: ["site-map", operatorId, view],
    queryFn: () =>
      request<SiteSnapshot>(`/site/map?view=${view}${operatorId ? `&operator_id=${operatorId}` : ""}`),
    refetchInterval: 2000,
  });

export const useAssistantStatus = () =>
  useQuery({
    queryKey: ["assistant-status"],
    queryFn: () => request<{ llm_configured: boolean; model: string | null; provider: string; fallback: string }>("/assistant/status"),
  });

/* ------------------------------------------------------------------ mutations */

export function useSendMessage() {
  return useMutation({
    mutationFn: (body: { message: string; operator_id: string; route?: string; task_id?: string }) =>
      post<AssistantReply>("/assistant/message", body),
  });
}

export function useStartTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => post<{ task: Task; eta: Eta }>(`/tasks/${taskId}/start`),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useCompleteTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, actualMin }: { taskId: string; actualMin?: number }) =>
      post<{
        task: Task;
        eta_outcome: {
          predicted_min: number;
          predicted_range: [number, number];
          actual_min: number;
          error_min: number;
          within_range: boolean;
        } | null;
        new_anomalies: unknown[];
      }>(`/tasks/${taskId}/complete`, { actual_time_min: actualMin ?? null }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useCompleteChecklist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, operatorId, items }: { taskId: string; operatorId: string; items: string[] }) =>
      post(`/safety/checklists/${taskId}/complete`, { operator_id: operatorId, completed_items: items }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useCreateIncident() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      operator_id: string;
      category: string;
      severity: string;
      description: string;
      location: string;
    }) => post<Incident>("/incidents", body),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useUpdateIncidentStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => patch<Incident>(`/incidents/${id}/status`, { status }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useAnomalyFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status, reason }: { id: number; status: string; reason?: string }) =>
      post<Anomaly>(`/insights/anomalies/${id}/feedback`, { status, reason: reason ?? null }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["anomalies"] }),
  });
}

export function useBookSlot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ slotId, operatorId }: { slotId: number; operatorId: string }) =>
      post<InstructorSlot & { confirmation: string }>(`/training/bookings/${slotId}`, { operator_id: operatorId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["instructors"] }),
  });
}

export function usePredictEta() {
  return useMutation({
    mutationFn: (body: {
      task_type: string;
      estimated_duration_min: number;
      weather: string;
      operator_skill: string;
      machine_age: number;
      operator_id?: string;
    }) => post<Eta>("/eta/predict", body),
  });
}
