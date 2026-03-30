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
    "Code Quality Agent": "agent-code-quality",
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
        <div className="glass-card rounded-xl p-6 border-slate-700/50 hover:border-slate-600/50 transition-colors duration-300">
            {/* Card header */}
            <div className="flex flex-col gap-3 mb-4">
                <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-slate-800 border border-white/10">
                        <Terminal className="w-5 h-5 text-slate-300" />
                    </div>
                    <h3 className="text-lg font-semibold text-white">
                        Agent Activity Log
                    </h3>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-sm text-green-400">
                        <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                        Live Server
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
                className="h-[320px] overflow-y-auto rounded-xl bg-[#0f172a] border border-slate-800 p-5 font-mono text-sm leading-relaxed space-y-2 shadow-inner whitespace-pre-wrap break-words"
            >
                {logs.length === 0 ? (
                    <p className="text-slate-500 italic mt-2 ml-2">
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
                                    isActive && "bg-white/5 -mx-2 px-2 py-0.5 rounded"
                                )}
                                style={{ animationDelay: `${index * 30}ms` }}
                            >
                                <span className="text-slate-500 shrink-0 select-none">
                                    [{log.timestamp}]
                                </span>
                                <span
                                    className={cn(
                                        "font-semibold shrink-0 drop-shadow-sm",
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
                                        log.level === "success" && "text-emerald-400",
                                        log.level === "info" && "text-slate-300"
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
