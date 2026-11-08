"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { AgentLog } from "@/types";
import { Terminal } from "lucide-react";

/**
 * Props for the AgentActivityLog component.
 */
interface AgentActivityLogProps {
    /** Array of agent log entries to display. */
    logs: AgentLog[];
    /** Name of the currently active agent (highlighted). */
    activeAgent?: string | null;
}

/** Maps agent names to CSS color classes. */
const agentColorMap: Record<string, string> = {
    "Manager Agent": "agent-manager",
    "Security Agent": "agent-security",
    "Performance Agent": "agent-performance",
    "Quality Agent": "agent-code-quality",
    "Reviewer Agent": "agent-reviewer",
};

/**
 * Terminal-style log panel showing agent activity in real-time.
 * Auto-scrolls to the bottom as new logs arrive.
 * Highlights the currently active agent with a glow effect.
 *
 * @param props - Log data and active agent name.
 */
export function AgentActivityLog({ logs, activeAgent }: AgentActivityLogProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div className="glass-card p-5">
            {/* Card header */}
            <div className="flex flex-col gap-2.5 mb-4">
                <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-md bg-secondary border border-border">
                        <Terminal className="w-4 h-4 text-muted-foreground" />
                    </div>
                    <h3 className="text-sm font-semibold text-foreground">
                        Agent Activity Log
                    </h3>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-xs text-primary">
                        <span className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse" />
                        Live
                    </div>
                    {activeAgent && activeAgent !== "System" && (
                        <div className="flex items-center gap-2 text-xs text-primary font-medium animate-fade-in">
                            <span className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse" />
                            {activeAgent}
                        </div>
                    )}
                </div>
            </div>

            <div
                ref={scrollRef}
                className="h-[320px] overflow-y-auto rounded-md bg-background border border-border p-4 font-mono text-sm leading-relaxed space-y-1.5 whitespace-pre-wrap break-words"
            >
                {logs.length === 0 ? (
                    <p className="text-muted-foreground italic mt-2 ml-2">
                        System ready. Waiting for audit task...
                    </p>
                ) : (
                    logs.map((log, index) => {
                        const isActive = activeAgent === log.agent && log.agent !== "System";

                        return (
                            <div
                                key={log.id}
                                className={cn(
                                    "flex gap-3 animate-fade-in break-words",
                                    isActive && "bg-secondary -mx-2 px-2 py-0.5 rounded"
                                )}
                                style={{ animationDelay: `${index * 30}ms` }}
                            >
                                <span className="text-muted-foreground shrink-0 select-none">
                                    [{log.timestamp}]
                                </span>
                                <span
                                    className={cn(
                                        "font-semibold shrink-0",
                                        agentColorMap[log.agent] ?? "text-foreground",
                                        isActive && "underline decoration-primary/40"
                                    )}
                                >
                                    {log.agent}:
                                </span>
                                <span
                                    className={cn(
                                        log.level === "warning" && "text-yellow-400",
                                        log.level === "error" && "text-red-400",
                                        log.level === "success" && "text-primary",
                                        log.level === "info" && "text-foreground/80"
                                    )}
                                >
                                    {log.message}
                                </span>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
