"use client";

import { useDashboardStore, RunMetrics } from "@/lib/store";

interface MetricsPanelProps {
  metrics: RunMetrics | null;
  estimated_time_ms: number;
  estimated_cost_usd: number;
}

export default function MetricsPanel({
  metrics,
  estimated_time_ms,
  estimated_cost_usd,
}: MetricsPanelProps) {
  const currentTime = metrics?.total_time_ms || 0;
  const currentCost = metrics?.total_cost_usd || 0;

  const progress = estimated_time_ms > 0 
    ? Math.min(100, (currentTime / estimated_time_ms) * 100) 
    : 0;

  const costProgress = estimated_cost_usd > 0
    ? Math.min(100, (currentCost / estimated_cost_usd) * 100)
    : 0;

  const providerBreakdown = metrics?.provider_breakdown || {};

  return (
    <div className="flex flex-col gap-4 p-4">
      {/* Time Progress */}
      <div className="rounded-lg border border-[#2a2a3a] bg-[#16161d] p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm text-[#8888aa]">⏱ Time</span>
          <span className="text-sm font-medium">
            {(currentTime / 1000).toFixed(1)}s / {(estimated_time_ms / 1000).toFixed(1)}s
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-[#2a2a3a]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#6366f1] to-[#22d3ee] transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Cost Progress */}
      <div className="rounded-lg border border-[#2a2a3a] bg-[#16161d] p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm text-[#8888aa]">💰 Cost</span>
          <span className="text-sm font-medium">
            ${currentCost.toFixed(4)} / ${estimated_cost_usd.toFixed(4)}
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-[#2a2a3a]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#22c55e] to-[#22d3ee] transition-all duration-500"
            style={{ width: `${costProgress}%` }}
          />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-[#2a2a3a] bg-[#16161d] p-3">
          <div className="text-xs text-[#8888aa]">Tasks</div>
          <div className="mt-1 text-xl font-bold">
            {metrics?.tasks_completed || 0}
            <span className="text-sm font-normal text-[#8888aa]">
              /{metrics?.tasks_total || 0}
            </span>
          </div>
        </div>

        <div className="rounded-lg border border-[#2a2a3a] bg-[#16161d] p-3">
          <div className="text-xs text-[#8888aa]">Parallel</div>
          <div className="mt-1 text-xl font-bold">
            {metrics?.parallelism || 0}
            <span className="text-sm font-normal text-[#8888aa]"> concurrent</span>
          </div>
        </div>

        <div className="rounded-lg border border-[#2a2a3a] bg-[#16161d] p-3">
          <div className="text-xs text-[#8888aa]">Tokens</div>
          <div className="mt-1 text-xl font-bold">
            {(metrics?.total_tokens || 0).toLocaleString()}
          </div>
        </div>

        <div className="rounded-lg border border-[#2a2a3a] bg-[#16161d] p-3">
          <div className="text-xs text-[#8888aa]">Reuse</div>
          <div className="mt-1 text-xl font-bold text-[#22d3ee]">
            {metrics?.reuse_pct?.toFixed(0) || 0}%
          </div>
        </div>
      </div>

      {/* Provider Breakdown */}
      {Object.keys(providerBreakdown).length > 0 && (
        <div className="rounded-lg border border-[#2a2a3a] bg-[#16161d] p-4">
          <div className="mb-3 text-sm text-[#8888aa]">☁️ Provider Usage</div>
          <div className="space-y-2">
            {Object.entries(providerBreakdown).map(([provider, count]) => (
              <div key={provider} className="flex items-center justify-between">
                <span className="text-xs text-[#8888aa]">{provider}</span>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-24 overflow-hidden rounded-full bg-[#2a2a3a]">
                    <div
                      className="h-full rounded-full bg-[#6366f1]"
                      style={{
                        width: `${(count / (metrics?.tasks_total || 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs font-medium">{count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
