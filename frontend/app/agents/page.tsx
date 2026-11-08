"use client";

import dynamic from "next/dynamic";

// React Flow is large: load it lazily, client-side only.
const AgentGraph = dynamic(
    () => import("@/components/agents/agent-graph").then((mod) => ({ default: mod.AgentGraph })),
    {
        ssr: false,
        loading: () => (
            <div className="h-full w-full animate-pulse rounded-xl bg-secondary/40" />
        ),
    }
);

const agents = [
    { name: "Manager", description: "Splits code into analyzable snippets and plans which agents run.", dot: "bg-[#b4a2fb]" },
    { name: "Security", description: "Finds vulnerabilities, injection flaws and exposed secrets.", dot: "bg-[#f58a85]" },
    { name: "Performance", description: "Spots slow queries, memory leaks and bottlenecks.", dot: "bg-[#f3d36b]" },
    { name: "Quality", description: "Checks error handling, naming and best practices.", dot: "bg-[#6fc9f2]" },
    { name: "Reviewer", description: "Merges every finding into one prioritized report.", dot: "bg-primary" },
];

/**
 * Agents page showing the multi-agent collaboration graph.
 */
export default function AgentsPage() {
    return (
        <div className="space-y-10">
            <div className="pt-4">
                <p className="eyebrow mb-4">How it works</p>
                <h1>Agent pipeline</h1>
                <p>How the agents collaborate on every audit.</p>
            </div>

            <div className="stagger grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {agents.map((agent, i) => (
                    <div
                        key={agent.name}
                        className="glass-card p-4"
                        style={{ "--i": i } as React.CSSProperties}
                    >
                        <div className="flex items-center gap-2">
                            <span className={`h-1.5 w-1.5 rounded-full ${agent.dot}`} />
                            <p className="eyebrow !text-foreground">{agent.name}</p>
                        </div>
                        <p className="mt-3 text-[13px] leading-relaxed text-muted-foreground">
                            {agent.description}
                        </p>
                    </div>
                ))}
            </div>

            <div className="glass-card h-[600px] w-full overflow-hidden p-4">
                <AgentGraph />
            </div>
        </div>
    );
}
