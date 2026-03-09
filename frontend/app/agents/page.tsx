"use client";

import dynamic from "next/dynamic";

const AgentGraph = dynamic(
    () => import("@/components/agents/agent-graph").then((mod) => ({ default: mod.AgentGraph })),
    {
        ssr: false,
        loading: () => (
            <div className="h-[600px] w-full rounded-xl border border-border bg-muted/20 flex items-center justify-center">
                <p className="text-sm text-muted-foreground">Loading graph...</p>
            </div>
        ),
    }
);

/**
 * Agents page showing the multi-agent collaboration graph.
 */
export default function AgentsPage() {
    return (
        <div className="space-y-8">
            {/* Page header */}
            <div>
                <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                    Agent Pipeline
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                    Visualize the multi-agent collaboration workflow.
                </p>
            </div>

            {/* Agent descriptions */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
                {[
                    {
                        name: "Manager Agent",
                        description: "Decomposes repository into analyzable code snippets",
                        color: "text-purple-400 bg-purple-500/10 border-purple-500/20",
                    },
                    {
                        name: "Security Agent",
                        description: "Detects vulnerabilities, injection flaws, and exposed secrets",
                        color: "text-red-400 bg-red-500/10 border-red-500/20",
                    },
                    {
                        name: "Performance Agent",
                        description: "Identifies N+1 queries, memory leaks, and bottlenecks",
                        color: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
                    },
                    {
                        name: "Code Quality Agent",
                        description: "Checks for error handling, naming, and best practices",
                        color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
                    },
                    {
                        name: "Reviewer Agent",
                        description: "Aggregates findings and generates remediation suggestions",
                        color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
                    },
                ].map((agent) => (
                    <div
                        key={agent.name}
                        className={`rounded-xl border p-3 transition-all hover:scale-[1.02] ${agent.color}`}
                    >
                        <p className="text-xs font-semibold">{agent.name}</p>
                        <p className="text-[11px] mt-1 opacity-70">{agent.description}</p>
                    </div>
                ))}
            </div>

            {/* Graph */}
            <div className="w-full h-[600px] bg-white/5 backdrop-blur-lg border border-white/10 rounded-xl p-6">
                <AgentGraph />
            </div>
        </div>
    );
}
