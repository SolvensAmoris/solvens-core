"use client";

import { useState } from "react";
import { useDashboardStore } from "@/lib/store";

interface SimulatorProps {
  onSimulate: (workflow: any) => Promise<void>;
  onRun: (workflow: any) => Promise<void>;
}

const PRESET_WORKFLOWS = [
  {
    name: "crm_generator",
    description: "Generate complete CRM with API, DB, UI",
    tasks: [
      { name: "fetch_requirements", provider: "anthropic" },
      { name: "design_database", provider: "anthropic", depends_on: ["fetch_requirements"] },
      { name: "design_api", provider: "anthropic", depends_on: ["design_database"] },
      { name: "design_ui", provider: "openai", depends_on: ["design_api"] },
      { name: "implement_database", provider: "openai", depends_on: ["design_database"] },
      { name: "implement_backend", provider: "openai", depends_on: ["design_api", "implement_database"] },
      { name: "implement_frontend", provider: "openai", depends_on: ["design_ui", "implement_backend"] },
      { name: "write_tests", provider: "openai", depends_on: ["implement_backend"] },
      { name: "write_docs", provider: "anthropic", depends_on: ["implement_backend", "implement_frontend"] },
      { name: "deploy", provider: "ollama", depends_on: ["implement_backend", "implement_frontend", "write_tests", "write_docs"] },
      { name: "verify", provider: "anthropic", depends_on: ["deploy"] },
    ],
  },
  {
    name: "doc_writer",
    description: "Document codebase with examples",
    tasks: [
      { name: "scan_repository", provider: "ollama" },
      { name: "read_source_files", provider: "anthropic", depends_on: ["scan_repository"] },
      { name: "generate_api_docs", provider: "openai", depends_on: ["read_source_files"] },
      { name: "generate_examples", provider: "openai", depends_on: ["read_source_files"] },
      { name: "generate_guides", provider: "anthropic", depends_on: ["generate_api_docs", "generate_examples"] },
      { name: "generate_readme", provider: "anthropic", depends_on: ["generate_guides"] },
    ],
  },
  {
    name: "audit_flow",
    description: "Audit code for security",
    tasks: [
      { name: "scan_codebase", provider: "ollama" },
      { name: "analyze_dependencies", provider: "ollama" },
      { name: "check_security", provider: "anthropic", depends_on: ["scan_codebase"] },
      { name: "check_quality", provider: "anthropic", depends_on: ["scan_codebase"] },
      { name: "analyze_results", provider: "anthropic", depends_on: ["check_security", "check_quality"] },
      { name: "generate_report", provider: "openai", depends_on: ["analyze_results", "analyze_dependencies"] },
    ],
  },
];

export default function Simulator({ onSimulate, onRun }: SimulatorProps) {
  const [selectedWorkflow, setSelectedWorkflow] = useState(PRESET_WORKFLOWS[0]);
  const [isSimulating, setIsSimulating] = useState(false);
  const { simulation, setSimulation } = useDashboardStore();

  const handleSimulate = async () => {
    setIsSimulating(true);
    try {
      await onSimulate(selectedWorkflow);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleRun = async () => {
    await onRun(selectedWorkflow);
  };

  const providerColors: Record<string, string> = {
    anthropic: "#6366f1",
    openai: "#22c55e",
    google: "#f59e0b",
    ollama: "#22d3ee",
    deepseek: "#ef4444",
  };

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      {/* Workflow Selector */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-[#8888aa]">
          Select Workflow
        </label>
        <div className="space-y-2">
          {PRESET_WORKFLOWS.map((wf) => (
            <button
              key={wf.name}
              onClick={() => setSelectedWorkflow(wf)}
              className={`w-full rounded-lg border p-3 text-left transition-all ${
                selectedWorkflow.name === wf.name
                  ? "border-[#6366f1] bg-[#6366f1]/10"
                  : "border-[#2a2a3a] bg-[#16161d] hover:border-[#6366f1]/50"
              }`}
            >
              <div className="font-medium">{wf.name}</div>
              <div className="mt-1 text-xs text-[#8888aa]">
                {wf.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Simulation Results */}
      {simulation && (
        <div className="rounded-lg border border-[#2a2a3a] bg-[#16161d] p-4">
          <div className="mb-3 text-sm font-medium text-[#22d3ee]">
            🔮 Simulation Results
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#8888aa]">Tasks</span>
              <span className="font-bold">{simulation.total_tasks}</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-[#8888aa]">Parallel Groups</span>
              <span className="font-bold">
                {Math.ceil(Math.sqrt(simulation.total_tasks))}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-[#8888aa]">Est. Time</span>
              <span className="font-bold">
                {(simulation.estimated_time_ms / 1000).toFixed(1)}s
              </span>
            </div>

            <div className="flex items-center justify-between border-t border-[#2a2a3a] pt-3">
              <span className="text-sm text-[#8888aa]">Est. Cost</span>
              <span className="text-xl font-bold text-[#22c55e]">
                ${simulation.estimated_cost_usd.toFixed(4)}
              </span>
            </div>

            {/* Provider Breakdown */}
            <div className="border-t border-[#2a2a3a] pt-3">
              <div className="mb-2 text-xs text-[#8888aa]">Provider Assignment</div>
              <div className="space-y-2">
                {Object.entries(simulation.provider_pct).map(
                  ([provider, pct]) => (
                    <div
                      key={provider}
                      className="flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <div
                          className="h-2 w-2 rounded-full"
                          style={{
                            backgroundColor: providerColors[provider] || "#6366f1",
                          }}
                        />
                        <span className="text-xs">{provider}</span>
                      </div>
                      <span className="text-xs font-medium">{pct}%</span>
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-auto space-y-2">
        <button
          onClick={handleSimulate}
          disabled={isSimulating}
          className="w-full rounded-lg border border-[#6366f1] bg-[#6366f1]/10 px-4 py-3 font-medium text-[#6366f1] transition-all hover:bg-[#6366f1]/20 disabled:opacity-50"
        >
          {isSimulating ? "⏳ Simulating..." : "🔮 Simulate"}
        </button>

        <button
          onClick={handleRun}
          disabled={!simulation}
          className="w-full rounded-lg bg-gradient-to-r from-[#6366f1] to-[#22d3ee] px-4 py-3 font-bold text-white transition-all hover:opacity-90 disabled:opacity-50"
        >
          ▶️ Run Workflow
        </button>
      </div>
    </div>
  );
}
