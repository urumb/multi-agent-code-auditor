"use client";

import { AuditForm } from "@/components/audit/audit-form";
import { ProgressIndicator } from "@/components/audit/progress-indicator";
import { AgentActivityLog } from "@/components/audit/agent-activity-log";
import { useAudit } from "@/hooks/use-audit";
import { toast } from "sonner";
import { CheckCircle, XCircle } from "lucide-react";
import { useEffect, useRef } from "react";

/**
 * Audit page for submitting code audits and monitoring agent progress.
 */
export default function AuditPage() {
    const { status, stages, logs, startAudit, reset } = useAudit();
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
                    <button
                        type="button"
                        onClick={reset}
                        className="rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
                    >
                        New Audit
                    </button>
                )}
            </div>

            <div className="max-w-5xl mx-auto flex flex-col gap-6">
                {/* Audit form */}
                <AuditForm onSubmit={handleSubmit} isRunning={status === "running"} />

                {/* Progress indicator */}
                {status !== "idle" && <ProgressIndicator stages={stages} />}

                {/* Agent activity log */}
                {status !== "idle" && <AgentActivityLog logs={logs} />}
            </div>
        </div>
    );
}
