"use client";

import { TaskNode } from "@/lib/store";

interface ActiveTasksProps {
  tasks: Record<string, TaskNode>;
}

const statusColors: Record<string, string> = {
  pending: "bg-[#4b5563]",
  running: "bg-blue-500 animate-pulse",
  done: "bg-green-500",
  error: "bg-red-500",
};

export default function ActiveTasks({ tasks }: ActiveTasksProps) {
  const taskList = Object.values(tasks);

  if (taskList.length === 0) {
    return (
      <div className="flex h-full items-center justify-center bg-[#16161d]">
        <div className="text-center text-[#8888aa]">
          <div className="text-4xl">🤖</div>
          <div className="mt-2">No active tasks</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-[#16161d]">
      <table className="w-full">
        <thead className="sticky top-0 bg-[#0f0f13] text-xs uppercase text-[#8888aa]">
          <tr>
            <th className="px-4 py-2 text-left">Task</th>
            <th className="px-4 py-2 text-left">Provider</th>
            <th className="px-4 py-2 text-left">Status</th>
            <th className="px-4 py-2 text-right">Tokens</th>
            <th className="px-4 py-2 text-right">Cost</th>
          </tr>
        </thead>
        <tbody className="text-sm">
          {taskList.map((task) => (
            <tr
              key={task.id}
              className="border-t border-[#2a2a3a] transition-colors hover:bg-[#1e1e2e]"
            >
              <td className="px-4 py-3 font-medium">{task.name}</td>
              <td className="px-4 py-3 text-[#8888aa]">
                <span className="rounded bg-[#2a2a3a] px-2 py-1 text-xs">
                  {task.provider}
                </span>
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <div
                    className={`h-2 w-2 rounded-full ${statusColors[task.status]}`}
                  />
                  <span className="capitalize">{task.status}</span>
                </div>
              </td>
              <td className="px-4 py-3 text-right text-[#8888aa]">
                {(task.tokens || 0).toLocaleString()}
              </td>
              <td className="px-4 py-3 text-right font-medium text-green-400">
                ${(task.cost_usd || 0).toFixed(4)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
