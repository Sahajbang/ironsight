import { create } from "zustand";

import type { GuideAction } from "../api/client";

/* ---------------- app ---------------- */

interface AppState {
  operatorId: string;
  setOperatorId: (id: string) => void;
  chatOpen: boolean;
  setChatOpen: (open: boolean) => void;
}

export const useApp = create<AppState>((set) => ({
  operatorId: "OP1001",
  setOperatorId: (operatorId) => set({ operatorId }),
  chatOpen: false,
  setChatOpen: (chatOpen) => set({ chatOpen }),
}));

/* ---------------- guide ---------------- */

export type GuidePhase = "idle" | "navigating" | "delivering" | "waiting";

interface GuideState {
  /** Off by default: a pointer that shows up uninvited while someone is operating a
   *  machine is a distraction, so the operator opts in and can switch it off instantly. */
  enabled: boolean;
  setEnabled: (enabled: boolean) => void;

  plan: GuideAction[];
  stepIndex: number;
  phase: GuidePhase;
  message: string;

  start: (plan: GuideAction[]) => void;
  setPhase: (phase: GuidePhase, message?: string) => void;
  advance: () => void;
  stop: () => void;
}

const STORAGE_KEY = "ironsight.guide.enabled";

function readEnabled(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export const useGuide = create<GuideState>((set, get) => ({
  enabled: readEnabled(),
  setEnabled: (enabled) => {
    try {
      localStorage.setItem(STORAGE_KEY, String(enabled));
    } catch {
      /* private mode — the toggle still works for this session */
    }
    set(enabled ? { enabled } : { enabled, plan: [], stepIndex: 0, phase: "idle" });
  },

  plan: [],
  stepIndex: 0,
  phase: "idle",
  message: "",

  start: (plan) => {
    if (!get().enabled || plan.length === 0) return;
    set({ plan, stepIndex: 0, phase: "navigating", message: "" });
  },
  setPhase: (phase, message) => set((s) => ({ phase, message: message ?? s.message })),
  advance: () =>
    set((s) => {
      const next = s.stepIndex + 1;
      return next >= s.plan.length
        ? { plan: [], stepIndex: 0, phase: "idle" as GuidePhase, message: "" }
        : { stepIndex: next, phase: "navigating" as GuidePhase };
    }),
  stop: () => set({ plan: [], stepIndex: 0, phase: "idle", message: "" }),
}));
