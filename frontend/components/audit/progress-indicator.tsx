import { cn } from "@/lib/utils";
import type { AuditStage } from "@/types";
import { Check, Loader2, Circle, AlertCircle } from "lucide-react";

/**
 * Props for the ProgressIndicator component.
 */
interface ProgressIndicatorProps {
    /** Ordered list of audit stages with their statuses. */
    stages: AuditStage[];
}

/**
 * Multi-stage progress indicator showing audit pipeline status.
 *
 * @param props - Stage data.
 */
export function ProgressIndicator({ stages }: ProgressIndicatorProps) {
    return (
        <div className="glass-card rounded-xl p-5">
            <h3 className="text-sm font-semibold text-foreground mb-5">
                Audit Progress
            </h3>
            <div className="space-y-0">
                {stages.map((stage, index) => (
                    <div key={stage.id} className="flex items-start gap-3">
                        {/* Vertical connector + icon */}
                        <div className="flex flex-col items-center">
                            <div
                                className={cn(
                                    "flex h-8 w-8 items-center justify-center rounded-full border-2 transition-all duration-300",
                                    stage.status === "completed" &&
                                    "border-emerald-500 bg-emerald-500/10",
                                    stage.status === "running" &&
                                    "border-primary bg-primary/10",
                                    stage.status === "pending" &&
                                    "border-border bg-muted/30",
                                    stage.status === "error" &&
                                    "border-red-500 bg-red-500/10"
                                )}
                            >
                                {stage.status === "completed" && (
                                    <Check className="h-4 w-4 text-emerald-400" />
                                )}
                                {stage.status === "running" && (
                                    <Loader2 className="h-4 w-4 text-primary animate-spin" />
                                )}
                                {stage.status === "pending" && (
                                    <Circle className="h-3 w-3 text-muted-foreground" />
                                )}
                                {stage.status === "error" && (
                                    <AlertCircle className="h-4 w-4 text-red-400" />
                                )}
                            </div>
                            {index < stages.length - 1 && (
                                <div
                                    className={cn(
                                        "w-0.5 h-8 transition-colors duration-300",
                                        stage.status === "completed"
                                            ? "bg-emerald-500/40"
                                            : "bg-border"
                                    )}
                                />
                            )}
                        </div>

                        {/* Label */}
                        <div className="pt-1.5">
                            <p
                                className={cn(
                                    "text-sm font-medium transition-colors duration-300",
                                    stage.status === "completed" && "text-emerald-400",
                                    stage.status === "running" && "text-primary",
                                    stage.status === "pending" && "text-muted-foreground",
                                    stage.status === "error" && "text-red-400"
                                )}
                            >
                                {stage.label}
                            </p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
