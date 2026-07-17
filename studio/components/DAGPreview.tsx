"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  MarkerType,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { TaskNode } from "@/lib/store";

interface DAGPreviewProps {
  nodes: TaskNode[];
  edges: { source: string; target: string }[];
  onNodeClick?: (nodeId: string) => void;
}

const statusColors: Record<string, string> = {
  pending: "#4b5563",
  running: "#3b82f6",
  done: "#22c55e",
  error: "#ef4444",
};

const providerIcons: Record<string, string> = {
  anthropic: "🤖",
  openai: "🧠",
  google: "🔮",
  ollama: "💻",
};

function TaskNodeComponent({ data }: { data: TaskNode }) {
  const color = statusColors[data.status] || statusColors.pending;
  const icon = providerIcons[data.provider] || "⚡";

  return (
    <div
      className="rounded-lg border-2 p-3 min-w-[160px] transition-all duration-300"
      style={{
        borderColor: color,
        backgroundColor: `${color}15`,
        boxShadow: data.status === "running" ? `0 0 20px ${color}40` : undefined,
      }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">{icon}</span>
        <div>
          <div className="font-semibold text-white text-sm">{data.name}</div>
          <div className="text-xs text-gray-400">{data.agent || data.provider}</div>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between">
        <span
          className="text-xs font-medium px-2 py-0.5 rounded"
          style={{ 
            backgroundColor: `${color}30`,
            color 
          }}
        >
          {data.status.toUpperCase()}
        </span>
        {data.cost !== undefined && (
          <span className="text-xs text-green-400">
            ${data.cost.toFixed(4)}
          </span>
        )}
      </div>
    </div>
  );
}

export default function DAGPreview({ nodes, edges, onNodeClick }: DAGPreviewProps) {
  // Layout nodes in topological order
  const layoutedNodes: Node[] = useMemo(() => {
    // Calculate levels based on dependencies
    const levels: Record<string, number> = {};
    
    const calcLevel = (nodeId: string, visited: Set<string> = new Set()): number => {
      if (visited.has(nodeId)) return 0;
      visited.add(nodeId);
      
      const deps = edges.filter(e => e.target === nodeId).map(e => e.source);
      if (deps.length === 0) {
        levels[nodeId] = 0;
        return 0;
      }
      
      const maxDepLevel = Math.max(...deps.map(d => calcLevel(d, visited)));
      levels[nodeId] = maxDepLevel + 1;
      return levels[nodeId];
    };
    
    nodes.forEach(n => calcLevel(n.id));
    
    // Group by level
    const byLevel: Record<number, string[]> = {};
    nodes.forEach(n => {
      const level = levels[n.id] || 0;
      if (!byLevel[level]) byLevel[level] = [];
      byLevel[level].push(n.id);
    });
    
    return nodes.map((node, idx) => {
      const level = levels[node.id] || 0;
      const nodesInLevel = byLevel[level] || [];
      const posInLevel = nodesInLevel.indexOf(node.id);
      
      return {
        id: node.id,
        type: "default",
        position: {
          x: level * 220 + 50,
          y: posInLevel * 120 + 50,
        },
        data: node,
      };
    });
  }, [nodes, edges]);

  const layoutedEdges: Edge[] = useMemo(
    () =>
      edges.map((edge, i) => ({
        id: `${edge.source}-${edge.target}-${i}`,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        animated: nodes.find(n => n.id === edge.target)?.status === "running",
        style: { 
          stroke: statusColors[nodes.find(n => n.id === edge.target)?.status || "pending"],
          strokeWidth: 2 
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "#6366f1",
        },
      })),
    [edges, nodes]
  );

  const [flowNodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [flowEdges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

  // Update when props change
  useMemo(() => {
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges]);

  return (
    <div className="h-full w-full bg-[#0a0a0f]">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => onNodeClick?.(node.id)}
        fitView
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#1a1a24"
        />
        <Controls />
      </ReactFlow>
      
      {/* Empty state */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center text-gray-500">
            <div className="text-4xl mb-2">📊</div>
            <div>Write a .cosmos file to see the DAG</div>
          </div>
        </div>
      )}
    </div>
  );
}
