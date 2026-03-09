"use client";

import { useCallback, useState, useEffect } from "react";
import {
    ReactFlow,
    Background,
    Controls,
    type Node,
    type Edge,
    type NodeTypes,
    Handle,
    Position,
    BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { cn } from "@/lib/utils";
import { Shield, Gauge, Code, Bot, Crown } from "lucide-react";

/** Node states for styling */
type NodeState = "idle" | "running" | "completed" | "error";

/**
 * Props for the custom agent node component.
 */
interface AgentNodeData {
    label: string;
    type: "manager" | "analyzer" | "reviewer";
    icon: string;
    state?: NodeState;
    [key: string]: unknown;
}

/** Maps icon names to Lucide components. */
const iconComponents: Record<string, React.ElementType> = {
    crown: Crown,
    shield: Shield,
    gauge: Gauge,
    code: Code,
    bot: Bot,
};

/**
 * Custom React Flow node for rendering an agent in the graph.
 */
function AgentNodeComponent({ data }: { data: AgentNodeData }) {
    const IconComp = iconComponents[data.icon] ?? Bot;
    const state = data.state || "idle";

    return (
        <div
            className={cn(
                "glass-card rounded-xl px-5 py-4 min-w-[180px] text-center transition-all duration-300 hover:-translate-y-1 hover:shadow-xl bg-[#0f172a] border-2",
                // Base colors by type (fallback if idle)
                state === "idle" && data.type === "manager" && "border-purple-500/20",
                state === "idle" && data.type === "analyzer" && "border-blue-500/20",
                state === "idle" && data.type === "reviewer" && "border-emerald-500/20",
                // State-based colors
                state === "idle" && "border-slate-700 opacity-80",
                state === "running" && "border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.5)] scale-105 bg-[#1e293b]",
                state === "completed" && "border-emerald-500",
                state === "error" && "border-red-500"
            )}
        >
            <Handle
                type="target"
                position={Position.Top}
                className="!bg-slate-400 !border-slate-800 !w-3 !h-3"
            />
            <div className="flex flex-col items-center gap-2.5">
                <div
                    className={cn(
                        "flex h-12 w-12 items-center justify-center rounded-full border shadow-inner transition-colors duration-300",
                        state === "idle" && "bg-slate-800 border-slate-700",
                        state === "running" && "bg-blue-500/20 border-blue-500/50",
                        state === "completed" && "bg-emerald-500/20 border-emerald-500/50",
                        state === "error" && "bg-red-500/20 border-red-500/50"
                    )}
                >
                    <IconComp
                        className={cn(
                            "h-6 w-6 transition-colors duration-300",
                            state === "idle" && "text-slate-400",
                            state === "running" && "text-blue-400 animate-pulse",
                            state === "completed" && "text-emerald-400",
                            state === "error" && "text-red-400"
                        )}
                    />
                </div>
                <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-semibold text-foreground tracking-tight">
                        {data.label}
                    </span>
                    <span
                        className={cn(
                            "text-[10px] uppercase tracking-wider font-bold",
                            state === "idle" && "text-slate-500",
                            state === "running" && "text-blue-400",
                            state === "completed" && "text-emerald-400",
                            state === "error" && "text-red-400"
                        )}
                    >
                        {state === "idle" && data.type}
                        {state !== "idle" && state}
                    </span>
                </div>
            </div>
            <Handle
                type="source"
                position={Position.Bottom}
                className="!bg-slate-400 !border-slate-800 !w-3 !h-3"
            />
        </div>
    );
}

/** Node type registry for React Flow. */
const nodeTypes: NodeTypes = {
    agent: AgentNodeComponent,
};

/** Initial Agent graph node definitions. */
const initialNodes: Node[] = [
    {
        id: "manager",
        type: "agent",
        position: { x: 300, y: 0 },
        data: { label: "Manager Agent", type: "manager", icon: "crown", state: "idle" },
    },
    {
        id: "security",
        type: "agent",
        position: { x: 50, y: 180 },
        data: { label: "Security Agent", type: "analyzer", icon: "shield", state: "idle" },
    },
    {
        id: "performance",
        type: "agent",
        position: { x: 300, y: 180 },
        data: { label: "Performance Agent", type: "analyzer", icon: "gauge", state: "idle" },
    },
    {
        id: "code-quality",
        type: "agent",
        position: { x: 550, y: 180 },
        data: { label: "Code Quality Agent", type: "analyzer", icon: "code", state: "idle" },
    },
    {
        id: "reviewer",
        type: "agent",
        position: { x: 300, y: 380 },
        data: { label: "Reviewer Agent", type: "reviewer", icon: "bot", state: "idle" },
    },
];

/** Edge definitions showing agent collaboration flow. */
const edges: Edge[] = [
    {
        id: "e-manager-security",
        source: "manager",
        target: "security",
        animated: true,
        style: { stroke: "#3b82f6", strokeWidth: 2, opacity: 0.5 },
    },
    {
        id: "e-manager-performance",
        source: "manager",
        target: "performance",
        animated: true,
        style: { stroke: "#3b82f6", strokeWidth: 2, opacity: 0.5 },
    },
    {
        id: "e-manager-codequality",
        source: "manager",
        target: "code-quality",
        animated: true,
        style: { stroke: "#3b82f6", strokeWidth: 2, opacity: 0.5 },
    },
    {
        id: "e-security-reviewer",
        source: "security",
        target: "reviewer",
        animated: true,
        style: { stroke: "#10b981", strokeWidth: 2, opacity: 0.5 },
    },
    {
        id: "e-performance-reviewer",
        source: "performance",
        target: "reviewer",
        animated: true,
        style: { stroke: "#10b981", strokeWidth: 2, opacity: 0.5 },
    },
    {
        id: "e-codequality-reviewer",
        source: "code-quality",
        target: "reviewer",
        animated: true,
        style: { stroke: "#10b981", strokeWidth: 2, opacity: 0.5 },
    },
];

/**
 * Interactive agent collaboration graph using React Flow.
 * Displays the multi-agent pipeline: Manager → Analyzers → Reviewer.
 */
export function AgentGraph() {
    // We'll simulate some state changes just for visual flair if needed,
    // but in a real app this would be driven by props.
    const [nodes, setNodes] = useState(initialNodes);

    useEffect(() => {
        // Simulate a running state sequence to demonstrate the visual upgrades
        const timer1 = setTimeout(() => {
            setNodes((nds) => nds.map((n) => (n.id === "manager" ? { ...n, data: { ...n.data, state: "completed" } } : n)));
            setNodes((nds) => nds.map((n) => (n.type === "agent" && n.id !== "manager" && n.id !== "reviewer" ? { ...n, data: { ...n.data, state: "running" } } : n)));
        }, 1500);

        return () => clearTimeout(timer1);
    }, []);

    const onInit = useCallback(() => {
        // Graph initialized
    }, []);

    return (
        <div className="h-[600px] w-full rounded-xl overflow-hidden border border-slate-800 bg-[#020617] shadow-inner">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                onInit={onInit}
                fitView
                fitViewOptions={{ padding: 0.3 }}
                proOptions={{ hideAttribution: true }}
                className="bg-[#020617]"
            >
                <Background
                    variant={BackgroundVariant.Dots}
                    gap={20}
                    size={1.5}
                    color="#334155"
                />
                <Controls
                    className="!bg-slate-800 !border-slate-700 !rounded-lg !shadow-lg [&>button]:!bg-slate-800 [&>button]:!border-slate-700 [&>button]:!text-slate-300 [&>button:hover]:!bg-slate-700"
                />
            </ReactFlow>
        </div>
    );
}
