import Link from "next/link";
import { cn } from "@/lib/utils";
import type { RecentAudit, AuditStatus } from "@/types";
import { GitBranch, Clock } from "lucide-react";

/**
 * Props for the RecentAudits component.
 */
interface RecentAuditsProps {
    /** List of recent audit entries. */
    audits: RecentAudit[];
}

/** Status badge configuration mapping. */
const statusConfig: Record<AuditStatus, { label: string; classes: string; dotColor: string; pulsing: boolean }> = {
    idle: { label: "Idle", classes: "bg-muted text-muted-foreground border-transparent", dotColor: "bg-muted-foreground", pulsing: false },
    pending: { label: "Pending", classes: "bg-muted text-muted-foreground border-transparent", dotColor: "bg-muted-foreground", pulsing: true },
    running: { label: "Running", classes: "bg-primary/10 text-primary border-primary/20", dotColor: "bg-primary", pulsing: true },
    completed: { label: "Completed", classes: "bg-primary/10 text-primary border-primary/20", dotColor: "bg-primary", pulsing: false },
    failed: { label: "Failed", classes: "bg-red-500/10 text-red-400 border-red-500/20", dotColor: "bg-red-500", pulsing: false },
};

/**
 * Recent audits list component for the dashboard. Each row links to its
 * full report in History.
 *
 * @param props - List of recent audits.
 */
export function RecentAudits({ audits }: RecentAuditsProps) {
    return (
        <div className="glass-card p-6 h-full flex flex-col">
            <h3 className="eyebrow mb-4">Recent audits</h3>
            <div className="space-y-1.5 flex-1">
                {audits.map((audit) => {
                    // A job can be "completed" (the run finished) while
                    // every file inside it errored/timed out — that reads
                    // very differently from a genuinely clean result, so it
                    // gets its own badge instead of a plain green "Completed".
                    const hasErrors = (audit.files_errored ?? 0) > 0;
                    const config =
                        audit.status === "completed" && hasErrors
                            ? { label: "Errored", classes: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20", dotColor: "bg-yellow-400", pulsing: false }
                            : (statusConfig[audit.status] ?? statusConfig.idle);
                    return (
                        <Link
                            key={audit.id}
                            href={`/history/${audit.id}`}
                            className="group flex flex-col sm:flex-row sm:items-center gap-3 rounded-md border border-transparent px-3 py-2.5 transition-colors duration-150 hover:bg-secondary"
                        >
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-secondary border border-border">
                                    <GitBranch className="h-3.5 w-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-foreground truncate">
                                        {audit.repository}
                                    </p>
                                    <div className="flex items-center gap-1.5 mt-0.5">
                                        <Clock className="h-3 w-3 text-muted-foreground" />
                                        <span className="text-xs text-muted-foreground">
                                            {new Date(audit.date).toLocaleDateString("en-US", {
                                                month: "short",
                                                day: "numeric",
                                                hour: "2-digit",
                                                minute: "2-digit",
                                            })}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0">
                                {audit.status === "completed" && (
                                    <span className="text-xs font-medium text-muted-foreground whitespace-nowrap">
                                        {hasErrors
                                            ? `${audit.files_errored} file(s) errored`
                                            : `${audit.findings} findings`}
                                    </span>
                                )}
                                <span
                                    className={cn(
                                        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
                                        config.classes
                                    )}
                                >
                                    <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", config.dotColor)} />
                                    {config.label}
                                </span>
                            </div>
                        </Link>
                    );
                })}
            </div>
        </div>
    );
}
