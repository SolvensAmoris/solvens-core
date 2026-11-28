"use client";

import { create } from "zustand";

export type TaskStatus = "pending" | "running" | "done" | "error";

export type TaskNode = {
  id: string;
  name: string;
  provider: string;
  model: string;
  status: TaskStatus;
  dependencies: string[];
  tokens?: number;
  cost_usd?: number;
};

export type RunMetrics = {
  total_time_ms: number;
  total_cost_usd: number;
  total_tokens: number;
  parallelism: number;
  reuse_pct: number;
  tasks_completed: number;
  tasks_total: number;
  provider_breakdown: Record<string, number>;
};

export type SimulationNode = {
  id: string;
  type?: string;
  data: {
    label: string;
    provider: string;
    status?: string;
    estimated_cost?: number;
    [key: string]: unknown;
  };
};

export type Simulation = {
  workflow_name: string;
  total_tasks: number;
  estimated_time_ms: number;
  estimated_cost_usd: number;
  parallel_groups: number;
  provider_pct: Record<string, number>;
  providers: Record<string, number>;
  dag: {
    nodes: SimulationNode[];
    edges: { source: string; target: string; type?: string }[];
  };
};

export type RunState = {
  run_id: string;
  workflow_name: string;
  status: string;
  tasks: Record<string, TaskNode>;
  metrics: RunMetrics;
  estimated_time_ms: number;
  estimated_cost_usd: number;
};

export type DashboardLog = {
  type: string;
  task?: string;
  message: string;
  timestamp: number;
};

type DashboardState = {
  simulation: Simulation | null;
  currentRun: RunState | null;
  logs: DashboardLog[];
  setSimulation: (simulation: Simulation | null) => void;
  setCurrentRun: (run: RunState | null) => void;
  updateTask: (taskId: string, updates: Partial<TaskNode>) => void;
  updateMetrics: (metrics: Partial<RunMetrics>) => void;
  addLog: (log: Omit<DashboardLog, "timestamp"> & { timestamp?: number }) => void;
  reset: () => void;
};

export const useDashboardStore = create<DashboardState>((set) => ({
  simulation: null,
  currentRun: null,
  logs: [],
  setSimulation: (simulation) => set({ simulation }),
  setCurrentRun: (currentRun) => set({ currentRun }),
  updateTask: (taskId, updates) =>
    set((state) => {
      if (!state.currentRun || !state.currentRun.tasks[taskId]) return state;
      return {
        currentRun: {
          ...state.currentRun,
          tasks: {
            ...state.currentRun.tasks,
            [taskId]: { ...state.currentRun.tasks[taskId], ...updates },
          },
        },
      };
    }),
  updateMetrics: (metrics) =>
    set((state) => {
      if (!state.currentRun) return state;
      return {
        currentRun: {
          ...state.currentRun,
          metrics: { ...state.currentRun.metrics, ...metrics },
        },
      };
    }),
  addLog: (log) =>
    set((state) => ({
      logs: [...state.logs, { ...log, timestamp: log.timestamp ?? Date.now() }].slice(-1000),
    })),
  reset: () => set({ currentRun: null, logs: [] }),
}));
