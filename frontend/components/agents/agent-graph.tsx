"use client";

import { useCallback, useMemo } from "react";
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
type NodeState = "idle" | "running" | "completed" | "failed";

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
                "glass-card rounded-xl px-5 py-4 min-w-[180px] text-center transition-all duration-300 hover:-translate-y-1 hover:shadow-xl bg-[#101010] border-2",
                // State-based colors
                state === "idle" && "border-[#27272a] opacity-80",
                state === "running" && "border-primary shadow-[0_0_15px_rgba(34,197,94,0.5)] scale-105 bg-[#151515]",
                state === "completed" && "border-primary",
                state === "failed" && "border-red-500"
            )}
        >
            <Handle
                type="target"
                position={Position.Top}
                className="!bg-zinc-400 !border-[#27272a] !w-3 !h-3"
            />
            <div className="flex flex-col items-center gap-2.5">
                <div
                    className={cn(
                        "flex h-12 w-12 items-center justify-center rounded-full border shadow-inner transition-colors duration-300",
                        state === "idle" && "bg-[#151515] border-[#27272a]",
                        state === "running" && "bg-primary/20 border-primary/50",
                        state === "completed" && "bg-primary/20 border-primary/50",
                        state === "failed" && "bg-red-500/20 border-red-500/50"
                    )}
                >
                    <IconComp
                        className={cn(
                            "h-6 w-6 transition-colors duration-300",
                            state === "idle" && "text-zinc-400",
                            state === "running" && "text-primary animate-pulse",
                            state === "completed" && "text-primary",
                            state === "failed" && "text-red-500"
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
                            state === "idle" && "text-zinc-500",
                            state === "running" && "text-primary",
                            state === "completed" && "text-primary",
                            state === "failed" && "text-red-500"
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
                className="!bg-zinc-400 !border-[#27272a] !w-3 !h-3"
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
        data: { label: "Security Agent", type: "analyzer", icon: "shield" },
    },
    {
        id: "performance",
        type: "agent",
        position: { x: 300, y: 180 },
        data: { label: "Performance Agent", type: "analyzer", icon: "gauge" },
    },
    {
        id: "code-quality",
        type: "agent",
        position: { x: 550, y: 180 },
        data: { label: "Quality Agent", type: "analyzer", icon: "code" },
    },
    {
        id: "reviewer",
        type: "agent",
        position: { x: 300, y: 380 },
        data: { label: "Reviewer Agent", type: "reviewer", icon: "bot" },
    },
];

/** Edge definitions showing agent collaboration flow. */
const edges: Edge[] = [
    {
        id: "e-manager-security",
        source: "manager",
        target: "security",
        animated: true,
        style: { stroke: "#22c55e", strokeWidth: 2, opacity: 0.5 },
    },
    {
        id: "e-manager-performance",
        source: "manager",
        target: "performance",
        animated: true,
        style: { stroke: "#22c55e", strokeWidth: 2, opacity: 0.5 },
    },
    {
        id: "e-manager-codequality",
        source: "manager",
        target: "code-quality",
        animated: true,
        style: { stroke: "#22c55e", strokeWidth: 2, opacity: 0.5 },
    },
    {
        id: "e-security-reviewer",
        source: "security",
        target: "reviewer",
        animated: true,
        style: { stroke: "#22c55e", strokeWidth: 2, opacity: 0.5 },
    },
    {
        id: "e-performance-reviewer",
        source: "performance",
        target: "reviewer",
        animated: true,
        style: { stroke: "#22c55e", strokeWidth: 2, opacity: 0.5 },
    },
    {
        id: "e-codequality-reviewer",
        source: "code-quality",
        target: "reviewer",
        animated: true,
        style: { stroke: "#22c55e", strokeWidth: 2, opacity: 0.5 },
    },
];

/**
 * Interactive agent collaboration graph using React Flow.
 * Displays the multi-agent pipeline: Manager → Analyzers → Reviewer.
 */
interface AgentGraphProps {
    nodeStates?: Partial<Record<string, NodeState>>;
}

export function AgentGraph({ nodeStates = {} }: AgentGraphProps) {
    const nodes = useMemo(
        () =>
            initialNodes.map((node) => ({
                ...node,
                data: {
                    ...node.data,
                    state: nodeStates[node.id] ?? "idle",
                },
            })),
        [nodeStates]
    );

    const onInit = useCallback(() => {
        // Graph initialized
    }, []);

    return (
        <div className="h-full min-h-[360px] w-full rounded-xl overflow-hidden border border-[#27272a] bg-[#050505] shadow-inner">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                onInit={onInit}
                fitView
                fitViewOptions={{ padding: 0.3 }}
                proOptions={{ hideAttribution: true }}
                className="bg-[#050505]"
            >
                <Background
                    variant={BackgroundVariant.Dots}
                    gap={20}
                    size={1.5}
                    color="#27272a"
                />
                <Controls
                    className="!bg-[#151515] !border-[#27272a] !rounded-lg !shadow-lg [&>button]:!bg-[#151515] [&>button]:!border-[#27272a] [&>button]:!text-zinc-300 [&>button:hover]:!bg-[#27272a]"
                />
            </ReactFlow>
        </div>
    );
}
