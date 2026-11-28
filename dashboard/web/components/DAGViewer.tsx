"use client";

import { useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  MarkerType,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

interface DAGViewerProps {
  nodes: {
    id: string;
    data: {
      label: string;
      provider: string;
      status?: string;
      cost_usd?: number;
      estimated_cost?: number;
    };
  }[];
  edges: { source: string; target: string }[];
  onNodeClick?: (nodeId: string) => void;
}

const statusColors: Record<string, string> = {
  pending: "#4b5563",
  running: "#3b82f6",
  done: "#22c55e",
  error: "#ef4444",
};

function TaskNode({ data }: { data: DAGViewerProps["nodes"][0]["data"] }) {
  const status = data.status || "pending";
  const color = statusColors[status] || statusColors.pending;

  return (
    <div
      className="rounded-lg border-2 px-4 py-3 min-w-[140px] transition-all duration-300"
      style={{
        borderColor: color,
        backgroundColor: `${color}15`,
        boxShadow: status === "running" ? `0 0 20px ${color}40` : undefined,
      }}
    >
      <div className="text-sm font-semibold text-white">{data.label}</div>
      <div className="mt-1 flex items-center justify-between">
        <span className="text-xs text-[#8888aa]">{data.provider}</span>
        <span
          className="text-xs font-medium"
          style={{ color }}
        >
          {data.status?.toUpperCase() || "PENDING"}
        </span>
      </div>
      {data.cost_usd !== undefined && (
        <div className="mt-1 text-xs text-[#8888aa]">
          ${data.cost_usd.toFixed(4)}
        </div>
      )}
    </div>
  );
}

export default function DAGViewer({ nodes, edges, onNodeClick }: DAGViewerProps) {
  const initialNodes: Node[] = useMemo(
    () =>
      nodes.map((node, index) => ({
        id: node.id,
        position: {
          x: (index % 4) * 200 + 50,
          y: Math.floor(index / 4) * 150 + 50,
        },
        data: {
          ...node.data,
          label: node.data.label,
        },
        type: "default",
      })),
    [nodes]
  );

  const initialEdges: Edge[] = useMemo(
    () =>
      edges.map((edge) => ({
        id: `${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        animated: true,
        style: { stroke: "#6366f1", strokeWidth: 2 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "#6366f1",
        },
      })),
    [edges]
  );

  const [flowNodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [flowEdges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClickHandler = useCallback(
    (_: unknown, node: Node) => {
      if (onNodeClick) {
        onNodeClick(node.id);
      }
    },
    [onNodeClick]
  );

  // Update nodes when data changes
  useMemo(() => {
    setNodes(
      nodes.map((node, index) => ({
        id: node.id,
        position: {
          x: (index % 4) * 200 + 50,
          y: Math.floor(index / 4) * 150 + 50,
        },
        data: node.data,
        type: "default",
      }))
    );
  }, [nodes, setNodes]);

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClickHandler}
        fitView
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#2a2a3a"
        />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const status = String(node.data?.status ?? "pending");
            return statusColors[status as keyof typeof statusColors] || statusColors.pending;
          }}
          maskColor="rgba(0, 0, 0, 0.8)"
          style={{ backgroundColor: "#16161d" }}
        />
      </ReactFlow>
    </div>
  );
}
