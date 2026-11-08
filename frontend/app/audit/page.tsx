"use client";

import { AuditForm } from "@/components/audit/audit-form";
import { ProgressIndicator } from "@/components/audit/progress-indicator";
import { AgentActivityLog } from "@/components/audit/agent-activity-log";
import dynamic from "next/dynamic";

// React Flow is large - only fetch it once an audit is actually running.
const AgentGraph = dynamic(
    () => import("@/components/agents/agent-graph").then((m) => m.AgentGraph),
    { ssr: false, loading: () => <div className="h-full w-full animate-pulse rounded-xl bg-secondary/40" /> }
);
import { useAudit } from "@/hooks/use-audit";
import { exportAuditAsJson } from "@/lib/export";
import { toast } from "sonner";
import { CheckCircle, XCircle, FileCode } from "lucide-react";
import { useEffect, useRef } from "react";

/**
 * Audit page for submitting code audits and monitoring agent progress.
 */
export default function AuditPage() {
    const {
        status,
        stages,
        logs,
        currentFile,
        currentAgent,
        result,
        duration,
        agentGraphStates,
        startAudit,
        reset,
    } = useAudit();
    const prevStatusRef = useRef(status);

    useEffect(() => {
        if (prevStatusRef.current === "running" && status === "completed") {
            toast.success("Audit completed successfully", {
                icon: <CheckCircle className="h-4 w-4 text-primary" />,
            });
        }
        if (prevStatusRef.current === "running" && status === "failed") {
            toast.error("Audit failed", {
                icon: <XCircle className="h-4 w-4 text-red-400" />,
            });
        }
        prevStatusRef.current = status;
    }, [status]);

    const handleSubmit = async (data: Parameters<typeof startAudit>[0]) => {
        toast.info("Audit started");
        await startAudit(data);
    };

    return (
        <div className="space-y-8">
            {/* Page header */}
            <div className="flex flex-wrap items-end justify-between gap-4 pt-4">
                <div>
                    <p className="eyebrow mb-4">New audit</p>
                    <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                        Run Audit
                    </h1>
                    <p className="text-sm text-muted-foreground mt-1">
                        Submit code for multi-agent analysis.
                    </p>
                </div>
                {status !== "idle" && (
                    <div className="flex gap-2">
                        {status === "completed" && result && (
                            <button
                                type="button"
                                onClick={() => exportAuditAsJson(result, "audit_report.json")}
                                className="btn-pill"
                            >
                                Export JSON
                            </button>
                        )}
                        <button
                            type="button"
                            onClick={reset}
                            className="rounded-full border border-border px-4 py-2 text-[0.8125rem] font-medium text-muted-foreground transition-colors duration-300 hover:border-[#34343a] hover:text-foreground"
                        >
                            New Audit
                        </button>
                    </div>
                )}
            </div>

            <div className="mx-auto flex max-w-5xl flex-col gap-5">
                {/* Audit form */}
                <AuditForm onSubmit={handleSubmit} isRunning={status === "running"} />

                {/* Current file indicator */}
                {currentFile && (
                    <div className="flex items-center gap-3 rounded-lg bg-primary/5 border border-primary/20 px-4 py-3 animate-fade-in">
                        <FileCode className="h-4 w-4 text-primary animate-pulse" />
                        <span className="text-sm text-foreground">
                            Processing:{" "}
                            <span className="font-mono font-medium text-primary">
                                {currentFile}
                            </span>
                        </span>
                    </div>
                )}

                {/* Progress indicator */}
                {status !== "idle" && (
                    <div className="relative">
                        <ProgressIndicator stages={stages} />
                        {status === "completed" && duration && (
                            <div className="absolute top-5 right-5 text-sm font-medium text-primary bg-primary/10 px-3 py-1 rounded-full animate-fade-in">
                                Completed in {duration}s
                            </div>
                        )}
                    </div>
                )}

                {status !== "idle" && (
                    <div className="w-full h-[420px] glass-card p-4 overflow-hidden">
                        <AgentGraph nodeStates={agentGraphStates} />
                    </div>
                )}

                {/* Agent activity log */}
                {status !== "idle" && (
                    <AgentActivityLog logs={logs} activeAgent={currentAgent} />
                )}
            </div>
        </div>
    );
}
