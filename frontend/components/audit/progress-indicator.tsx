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
        <div className="glass-card p-6">
            <h3 className="text-sm font-semibold text-foreground mb-6">
                Audit Progress
            </h3>
            <div className="flex flex-col space-y-0">
                {stages.map((stage, index) => (
                    <div key={stage.id} className="flex items-start gap-4">
                        {/* Vertical connector + icon */}
                        <div className="flex flex-col items-center">
                            <div
                                className={cn(
                                    "flex h-7 w-7 items-center justify-center rounded-full border transition-colors duration-300",
                                    stage.status === "completed" &&
                                    "border-primary bg-primary/10",
                                    stage.status === "running" &&
                                    "border-primary bg-primary/10",
                                    stage.status === "pending" &&
                                    "border-border bg-secondary/50",
                                    stage.status === "error" &&
                                    "border-destructive bg-destructive/10"
                                )}
                            >
                                {stage.status === "completed" && (
                                    <Check className="h-3.5 w-3.5 text-primary" />
                                )}
                                {stage.status === "running" && (
                                    <Loader2 className="h-3.5 w-3.5 text-primary animate-spin" />
                                )}
                                {stage.status === "pending" && (
                                    <Circle className="h-2.5 w-2.5 text-muted-foreground" />
                                )}
                                {stage.status === "error" && (
                                    <AlertCircle className="h-3.5 w-3.5 text-destructive" />
                                )}
                            </div>
                            {index < stages.length - 1 && (
                                <div
                                    className={cn(
                                        "w-px h-8 transition-colors duration-300 my-1",
                                        stage.status === "completed"
                                            ? "bg-primary/40"
                                            : "bg-border"
                                    )}
                                />
                            )}
                        </div>

                        {/* Label */}
                        <div className="pt-1">
                            <p
                                className={cn(
                                    "text-sm font-medium transition-colors duration-300",
                                    stage.status === "completed" && "text-foreground",
                                    stage.status === "running" && "text-primary",
                                    stage.status === "pending" && "text-muted-foreground",
                                    stage.status === "error" && "text-destructive"
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
