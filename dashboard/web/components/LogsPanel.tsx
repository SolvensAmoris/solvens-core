"use client";

import { useEffect, useRef } from "react";
import { useDashboardStore } from "@/lib/store";

interface LogsPanelProps {
  logs: { type: string; task?: string; message: string; timestamp: number }[];
}

export default function LogsPanel({ logs }: LogsPanelProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const getLogColor = (type: string) => {
    switch (type) {
      case "task_start":
        return "text-blue-400";
      case "task_end":
        return "text-green-400";
      case "task_error":
        return "text-red-400";
      case "metric_update":
        return "text-cyan-400";
      case "run_start":
        return "text-purple-400";
      case "run_end":
        return "text-yellow-400";
      default:
        return "text-[#8888aa]";
    }
  };

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <div className="flex h-full flex-col bg-[#16161d]">
      <div className="shrink-0 border-b border-[#2a2a3a] px-4 py-2">
        <span className="text-sm font-medium text-[#8888aa]">📜 Logs</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4 font-mono text-xs">
        {logs.length === 0 ? (
          <div className="flex h-full items-center justify-center text-[#8888aa]">
            <div className="text-center">
              <div className="text-4xl">📭</div>
              <div className="mt-2">No logs yet</div>
              <div className="mt-1 text-[10px]">
                Start a workflow to see logs
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            {logs.map((log, i) => (
              <div key={i} className={`${getLogColor(log.type)} flex gap-2`}>
                <span className="shrink-0 text-[#4b5563]">
                  {formatTime(log.timestamp)}
                </span>
                <span className="shrink-0">
                  {log.task && (
                    <span className="mr-2 rounded bg-[#2a2a3a] px-1">
                      {log.task}
                    </span>
                  )}
                </span>
                <span>{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}
