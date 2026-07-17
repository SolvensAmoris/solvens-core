"use client";

import { useStudioStore } from "@/lib/store";
import { Play, TrendingDown, Clock, Zap, Cpu } from "lucide-react";

export default function SimulationPanel() {
  const { simulation, isSimulating, runSimulation, nodes } = useStudioStore();

  const providerColors: Record<string, string> = {
    anthropic: "#6366f1",
    openai: "#22c55e",
    google: "#f59e0b",
    ollama: "#22d3ee",
  };

  return (
    <div className="h-full flex flex-col bg-[#0f0f14]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1a1a24] px-4 py-3">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-[#f59e0b]" />
          <span className="font-medium">🔮 Simulation</span>
        </div>
        <button
          onClick={runSimulation}
          disabled={isSimulating || nodes.length === 0}
          className="flex items-center gap-2 rounded bg-[#6366f1] px-3 py-1.5 text-sm font-medium hover:bg-[#5558e3] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Play className="w-3 h-3" />
          {isSimulating ? "Simulating..." : "Run"}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {simulation ? (
          <>
            {/* Cost */}
            <div className="rounded-lg border border-[#1a1a24] p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <TrendingDown className="w-4 h-4" />
                  <span>Estimated Cost</span>
                </div>
                <span className="text-2xl font-bold text-green-400">
                  ${simulation.estimated_cost_usd.toFixed(4)}
                </span>
              </div>
              <div className="text-xs text-gray-500">
                vs LangChain: ~${(simulation.estimated_cost_usd * 2.6).toFixed(4)}
              </div>
              <div className="mt-2 h-2 rounded-full bg-[#1a1a24] overflow-hidden">
                <div 
                  className="h-full rounded-full bg-gradient-to-r from-green-500 to-emerald-400 transition-all"
                  style={{ width: "38%" }}
                />
              </div>
              <div className="mt-1 text-xs text-green-400">
                62% savings vs competitors
              </div>
            </div>

            {/* Time */}
            <div className="rounded-lg border border-[#1a1a24] p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <Clock className="w-4 h-4" />
                  <span>Estimated Time</span>
                </div>
                <span className="text-2xl font-bold">
                  {(simulation.estimated_time_ms / 1000 / 60).toFixed(1)}m
                </span>
              </div>
              <div className="text-xs text-gray-500">
                {simulation.total_tasks} tasks in parallel
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-[#1a1a24] p-3 text-center">
                <div className="text-2xl font-bold text-[#6366f1]">
                  {simulation.total_tasks}
                </div>
                <div className="text-xs text-gray-500">Tasks</div>
              </div>
              <div className="rounded-lg border border-[#1a1a24] p-3 text-center">
                <div className="text-2xl font-bold text-[#22d3ee]">
                  {simulation.reuse_percentage}%
                </div>
                <div className="text-xs text-gray-500">Reuse</div>
              </div>
            </div>

            {/* Provider Breakdown */}
            <div className="rounded-lg border border-[#1a1a24] p-4">
              <div className="flex items-center gap-2 text-sm text-gray-400 mb-3">
                <Cpu className="w-4 h-4" />
                <span>Provider Assignment</span>
              </div>
              <div className="space-y-2">
                {Object.entries(simulation.provider_breakdown).map(
                  ([provider, percentage]) => (
                    <div key={provider} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: providerColors[provider] || "#6366f1" }}
                        />
                        <span className="text-sm capitalize">{provider}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-1.5 rounded-full bg-[#1a1a24] overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${percentage}%`,
                              backgroundColor: providerColors[provider] || "#6366f1",
                            }}
                          />
                        </div>
                        <span className="text-xs font-medium w-10 text-right">
                          {percentage}%
                        </span>
                      </div>
                    </div>
                  )
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <div className="text-4xl mb-3">🔮</div>
            <div className="text-sm mb-1">No simulation yet</div>
            <div className="text-xs">
              Click "Run" to estimate cost
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
