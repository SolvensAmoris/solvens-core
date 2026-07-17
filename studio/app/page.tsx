"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useStudioStore } from "@/lib/store";
import MonacoEditor from "@/components/MonacoEditor";
import Copilot from "@/components/Copilot";
import SimulationPanel from "@/components/SimulationPanel";
import { Folder, Search, Layout, GitBranch, Plus } from "lucide-react";

// Dynamic imports for client-only components
const DAGPreview = dynamic(() => import("@/components/DAGPreview"), { ssr: false });

export default function StudioPage() {
  const {
    files,
    activeFile,
    setActiveFile,
    updateFile,
    nodes,
    edges,
    parseDAG,
    sidebarTab,
    setSidebarTab,
    isRunning,
    runWorkflow,
    simulation,
  } = useStudioStore();

  const [rightPanel, setRightPanel] = useState<"dag" | "simulation">("dag");

  const activeFileContent = files.find((f) => f.name === activeFile)?.content || "";

  // Parse DAG when file changes
  useEffect(() => {
    parseDAG(activeFileContent);
  }, [activeFileContent, parseDAG]);

  const handleEditorChange = (value: string) => {
    updateFile(activeFile, value);
  };

  return (
    <div className="flex h-full">
      {/* Left Sidebar */}
      <div className="w-64 shrink-0 border-r border-[#1a1a24] bg-[#0f0f14] flex flex-col">
        {/* Tabs */}
        <div className="flex border-b border-[#1a1a24]">
          <button
            onClick={() => setSidebarTab("files")}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs ${
              sidebarTab === "files"
                ? "text-white border-b-2 border-[#6366f1]"
                : "text-gray-500 hover:text-white"
            }`}
          >
            <Folder className="w-3 h-3" />
            Files
          </button>
          <button
            onClick={() => setSidebarTab("hub")}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs ${
              sidebarTab === "hub"
                ? "text-white border-b-2 border-[#6366f1]"
                : "text-gray-500 hover:text-white"
            }`}
          >
            <GitBranch className="w-3 h-3" />
            Hub
          </button>
          <button
            onClick={() => setSidebarTab("templates")}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs ${
              sidebarTab === "templates"
                ? "text-white border-b-2 border-[#6366f1]"
                : "text-gray-500 hover:text-white"
            }`}
          >
            <Layout className="w-3 h-3" />
            Templates
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-2">
          {sidebarTab === "files" && (
            <div className="space-y-1">
              {files.map((file) => (
                <button
                  key={file.name}
                  onClick={() => setActiveFile(file.name)}
                  className={`w-full flex items-center gap-2 rounded px-2 py-1.5 text-sm text-left transition-colors ${
                    activeFile === file.name
                      ? "bg-[#6366f1]/20 text-white"
                      : "text-gray-400 hover:bg-[#1a1a24] hover:text-white"
                  }`}
                >
                  <span className="text-gray-500">📄</span>
                  <span className="truncate">{file.name}</span>
                </button>
              ))}
              <button className="w-full flex items-center gap-2 rounded px-2 py-1.5 text-sm text-gray-500 hover:bg-[#1a1a24] hover:text-white transition-colors">
                <Plus className="w-3 h-3" />
                <span>New File</span>
              </button>
            </div>
          )}

          {sidebarTab === "hub" && (
            <div className="space-y-2">
              <div className="text-xs text-gray-500 mb-2">Featured Workflows</div>
              {[
                { name: "@solvens/crm-generator", desc: "Complete SaaS from spec" },
                { name: "@solvens/doc-writer", desc: "Document any codebase" },
                { name: "@solvens/audit-flow", desc: "Security audit" },
              ].map((wf) => (
                <div
                  key={wf.name}
                  className="rounded border border-[#1a1a24] p-2 hover:border-[#6366f1] cursor-pointer transition-colors"
                >
                  <div className="text-sm text-white">{wf.name}</div>
                  <div className="text-xs text-gray-500">{wf.desc}</div>
                </div>
              ))}
            </div>
          )}

          {sidebarTab === "templates" && (
            <div className="space-y-2">
              <div className="text-xs text-gray-500 mb-2">Quick Start</div>
              {[
                { name: "SaaS Starter", icon: "🚀", desc: "Auth + DB + API" },
                { name: "Data Pipeline", icon: "🔄", desc: "ETL with Pandas" },
                { name: "Agent Swarm", icon: "🐝", desc: "10 agents collab" },
              ].map((tmpl) => (
                <div
                  key={tmpl.name}
                  className="rounded border border-[#1a1a24] p-2 hover:border-[#6366f1] cursor-pointer transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span>{tmpl.icon}</span>
                    <span className="text-sm text-white">{tmpl.name}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">{tmpl.desc}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Search */}
        <div className="p-2 border-t border-[#1a1a24]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-500" />
            <input
              type="text"
              placeholder="Search..."
              className="w-full rounded bg-[#1a1a24] pl-8 pr-3 py-1.5 text-sm placeholder:text-gray-600 focus:outline-none focus:ring-1 focus:ring-[#6366f1]"
            />
          </div>
        </div>
      </div>

      {/* Main Editor */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Editor */}
        <div className="flex-1 min-h-0">
          <MonacoEditor
            value={activeFileContent}
            onChange={handleEditorChange}
          />
        </div>

        {/* Bottom Panel - DAG or Simulation */}
        <div className="h-80 shrink-0 border-t border-[#1a1a24]">
          {/* Tabs */}
          <div className="flex border-b border-[#1a1a24] bg-[#0f0f14]">
            <button
              onClick={() => setRightPanel("dag")}
              className={`px-4 py-2 text-sm ${
                rightPanel === "dag"
                  ? "text-white border-b-2 border-[#6366f1]"
                  : "text-gray-500 hover:text-white"
              }`}
            >
              📊 DAG Preview
            </button>
            <button
              onClick={() => setRightPanel("simulation")}
              className={`px-4 py-2 text-sm ${
                rightPanel === "simulation"
                  ? "text-white border-b-2 border-[#f59e0b]"
                  : "text-gray-500 hover:text-white"
              }`}
            >
              🔮 Simulation
              {simulation && (
                <span className="ml-2 text-xs bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded">
                  ${simulation.estimated_cost_usd.toFixed(4)}
                </span>
              )}
            </button>
          </div>

          {/* Content */}
          <div className="h-full">
            {rightPanel === "dag" ? (
              <DAGPreview nodes={nodes} edges={edges} />
            ) : (
              <SimulationPanel />
            )}
          </div>
        </div>
      </div>

      {/* Right Sidebar - Copilot */}
      <div className="w-80 shrink-0 border-l border-[#1a1a24]">
        <Copilot />
      </div>

      {/* Status Bar */}
      <div className="absolute bottom-0 left-0 right-0 h-6 status-bar flex items-center justify-between px-4 text-xs text-white/80">
        <div className="flex items-center gap-4">
          <span>🌵 SOLVENS Studio v1.0</span>
          <span>|</span>
          <span>{nodes.length} tasks</span>
          <span>|</span>
          <span>{edges.length} dependencies</span>
        </div>
        <div className="flex items-center gap-4">
          {isRunning && (
            <>
              <span className="flex items-center gap-1">
                <span className="animate-pulse">●</span> Running
              </span>
              <span>|</span>
            </>
          )}
          <span>
            {activeFile}
          </span>
          <span>|</span>
          <span>Cosmos Language</span>
        </div>
      </div>
    </div>
  );
}
