"use client";

import { AuditForm } from "@/components/audit/audit-form";
import { ProgressIndicator } from "@/components/audit/progress-indicator";
import { AgentActivityLog } from "@/components/audit/agent-activity-log";
import { useAudit } from "@/hooks/use-audit";
import { toast } from "sonner";
import { CheckCircle, XCircle, FileCode } from "lucide-react";
import { useEffect, useRef } from "react";

/**
 * Audit page for submitting code audits and monitoring agent progress.
 */
export default function AuditPage() {
    const { status, stages, logs, currentFile, currentAgent, result, duration, startAudit, reset } = useAudit();
    const prevStatusRef = useRef(status);

    useEffect(() => {
        if (prevStatusRef.current === "running" && status === "completed") {
            toast.success("Audit completed successfully", {
                icon: <CheckCircle className="h-4 w-4 text-emerald-400" />,
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
            <div className="flex items-center justify-between">
                <div>
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
                                onClick={() => {
                                    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
                                    const url = URL.createObjectURL(blob);
                                    const a = document.createElement("a");
                                    a.href = url;
                                    a.download = "audit_report.json";
                                    document.body.appendChild(a);
                                    a.click();
                                    document.body.removeChild(a);
                                    URL.revokeObjectURL(url);
                                }}
                                className="rounded-lg border border-primary/20 bg-primary/10 px-4 py-2 text-sm font-medium text-primary hover:bg-primary/20 transition-all"
                            >
                                Export JSON
                            </button>
                        )}
                        <button
                            type="button"
                            onClick={reset}
                            className="rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
                        >
                            New Audit
                        </button>
                    </div>
                )}
            </div>

            <div className="max-w-5xl mx-auto flex flex-col gap-6">
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
                            <div className="absolute top-5 right-5 text-sm font-medium text-emerald-400 bg-emerald-400/10 px-3 py-1 rounded-full animate-fade-in">
                                Completed in {duration}s
                            </div>
                        )}
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
