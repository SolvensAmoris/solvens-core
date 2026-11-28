"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { useDashboardStore } from "@/lib/store";
import Simulator from "@/components/Simulator";
import MetricsPanel from "@/components/MetricsPanel";
import LogsPanel from "@/components/LogsPanel";
import ActiveTasks from "@/components/ActiveTasks";
import { useAuth } from "@/lib/auth";

// Dynamic import for React Flow (requires client-side only)
const DAGViewer = dynamic(() => import("@/components/DAGViewer"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center bg-[#0f0f13]">
      <div className="text-center text-[#8888aa]">
        <div className="text-4xl animate-pulse">🌌</div>
        <div className="mt-2">Loading DAG...</div>
      </div>
    </div>
  ),
});

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Dashboard() {
  const { simulation, currentRun, setSimulation, setCurrentRun, updateTask, updateMetrics, addLog, logs, reset } =
    useDashboardStore();
  const [activeTab, setActiveTab] = useState<"dag" | "tasks">("dag");
  const { user, loading, configured, signIn, apiFetch } = useAuth();

  // Authenticate, request a one-use server ticket, then open the socket.
  useEffect(() => {
    if (!currentRun || !user) return;
    let cancelled = false;
    let ws: WebSocket | null = null;

    const connect = async () => {
      try {
        const response = await apiFetch("/api/auth/ws-ticket", { method: "POST" });
        const { ticket } = await response.json();
        if (cancelled) return;
        ws = new WebSocket(
          `${API_URL.replace("http", "ws")}/ws/run/${currentRun.run_id}?ticket=${encodeURIComponent(ticket)}`,
        );

        ws.onopen = () => addLog({ type: "system", message: "Connected to run " + currentRun.run_id });
        ws.onmessage = (event) => {
          const msg = JSON.parse(event.data);
          const { type, data } = msg;
          switch (type) {
            case "task_start":
              updateTask(data.task, { status: "running" });
              addLog({ type: "task_start", task: data.task, message: `Started (${data.provider})` });
              break;
            case "task_end":
              updateTask(data.task, { status: "done", cost_usd: data.cost_usd, tokens: data.tokens });
              addLog({ type: "task_end", task: data.task, message: `Completed in ${(data.duration_ms / 1000).toFixed(2)}s` });
              break;
            case "task_error":
              updateTask(data.task, { status: "error" });
              addLog({ type: "task_error", task: data.task, message: data.error || "Error" });
              break;
            case "metric_update":
              updateMetrics(data);
              break;
            case "run_end":
              addLog({ type: "run_end", message: `Run completed - ${data.status}` });
              break;
          }
        };
        ws.onerror = () => addLog({ type: "error", message: "WebSocket connection error" });
        ws.onclose = () => addLog({ type: "system", message: "WebSocket disconnected" });
      } catch (err) {
        if (!cancelled) {
          console.error("WebSocket ticket error:", err);
          addLog({ type: "error", message: "Could not authorize WebSocket connection" });
        }
      }
    };

    void connect();
    return () => {
      cancelled = true;
      ws?.close();
    };
  }, [currentRun, user, apiFetch, updateTask, updateMetrics, addLog]);

  const handleSimulate = useCallback(async (workflow: any) => {
    try {
      const res = await apiFetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(workflow),
      });
      const data = await res.json();
      setSimulation(data);
      addLog({ type: "simulation", message: `Simulated: ${data.total_tasks} tasks in ${data.parallel_groups} groups` });
    } catch (err) {
      console.error("Simulate error:", err);
      addLog({ type: "error", message: "Simulation failed" });
    }
  }, [setSimulation, addLog, apiFetch]);

  const handleRun = useCallback(async (workflow: any) => {
    try {
      reset();
      const res = await apiFetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(workflow),
      });
      const data = await res.json();
      
      // Set initial run state from simulation
      if (simulation) {
        setCurrentRun({
          run_id: data.run_id,
          workflow_name: workflow.name,
          status: "running",
          tasks: Object.fromEntries(
            simulation.nodes.map((n) => [
              n.id,
              {
                id: n.id,
                name: n.id,
                provider: n.data.provider,
                model: "default",
                status: "pending",
              },
            ])
          ),
          metrics: {
            total_time_ms: 0,
            total_cost_usd: 0,
            total_tokens: 0,
            parallelism: 0,
            reuse_pct: 47,
            tasks_completed: 0,
            tasks_total: simulation.total_tasks,
            provider_breakdown: simulation.providers || {},
          },
          estimated_time_ms: simulation.estimated_time_ms,
          estimated_cost_usd: simulation.estimated_cost_usd,
        });
      }
      
      addLog({ type: "run_start", message: `Started run ${data.run_id}` });
    } catch (err) {
      console.error("Run error:", err);
      addLog({ type: "error", message: "Failed to start run" });
    }
  }, [simulation, reset, setCurrentRun, addLog, apiFetch]);

  // Prepare DAG nodes and edges
  const dagNodes = simulation?.dag?.nodes || currentRun
    ? (simulation?.dag?.nodes || currentRun?.tasks
        ? Object.values(currentRun?.tasks || {}).map((t) => ({
            id: t.id,
            data: {
              label: t.name,
              provider: t.provider,
              status: t.status,
              cost_usd: t.cost_usd,
            },
          }))
        : [])
    : [];

  const dagEdges = simulation?.dag?.edges || currentRun
    ? (simulation?.dag?.edges || Object.values(currentRun?.tasks || {}).flatMap((t) =>
        t.dependencies.map((dep) => ({ source: dep, target: t.id }))
      ))
    : [];

  if (!configured) {
    return <div className="flex h-full items-center justify-center text-amber-300">Dashboard OIDC configuration is missing.</div>;
  }
  if (loading) {
    return <div className="flex h-full items-center justify-center text-[#8888aa]">Loading secure session…</div>;
  }
  if (!user) {
    return (
      <div className="flex h-full items-center justify-center bg-[#0f0f13] text-white">
        <button onClick={() => void signIn()} className="rounded bg-indigo-600 px-5 py-3 font-medium hover:bg-indigo-500">
          Sign in to SOLVENS CORE
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left Panel - Simulator */}
      <div className="w-80 shrink-0 border-r border-[#2a2a3a] bg-[#0f0f13]">
        <div className="border-b border-[#2a2a3a] px-4 py-3">
          <h2 className="font-bold gradient-text">🚀 Simulator</h2>
        </div>
        <Simulator onSimulate={handleSimulate} onRun={handleRun} />
      </div>

      {/* Center Panel - DAG */}
      <div className="flex flex-1 flex-col">
        {/* Tab Bar */}
        <div className="flex border-b border-[#2a2a3a] bg-[#16161d]">
          <button
            onClick={() => setActiveTab("dag")}
            className={`px-6 py-3 text-sm font-medium transition-colors ${
              activeTab === "dag"
                ? "border-b-2 border-[#6366f1] text-white"
                : "text-[#8888aa] hover:text-white"
            }`}
          >
            🌌 DAG Visualization
          </button>
          <button
            onClick={() => setActiveTab("tasks")}
            className={`px-6 py-3 text-sm font-medium transition-colors ${
              activeTab === "tasks"
                ? "border-b-2 border-[#6366f1] text-white"
                : "text-[#8888aa] hover:text-white"
            }`}
          >
            🤖 Active Tasks
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === "dag" ? (
            <DAGViewer nodes={dagNodes} edges={dagEdges} />
          ) : (
            <ActiveTasks tasks={currentRun?.tasks || {}} />
          )}
        </div>
      </div>

      {/* Right Panel - Metrics & Logs */}
      <div className="flex w-80 shrink-0 flex-col border-l border-[#2a2a3a] bg-[#0f0f13]">
        {/* Metrics */}
        <div className="border-b border-[#2a2a3a]">
          <div className="border-b border-[#2a2a3a] px-4 py-3">
            <h2 className="font-bold text-[#8888aa]">📊 Metrics</h2>
          </div>
          <MetricsPanel
            metrics={currentRun?.metrics || null}
            estimated_time_ms={simulation?.estimated_time_ms || currentRun?.estimated_time_ms || 200000}
            estimated_cost_usd={simulation?.estimated_cost_usd || currentRun?.estimated_cost_usd || 0.18}
          />
        </div>

        {/* Logs */}
        <div className="flex-1 overflow-hidden">
          <LogsPanel logs={logs} />
        </div>
      </div>
    </div>
  );
}
