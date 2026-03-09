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
    idle: { label: "Idle", classes: "bg-muted text-muted-foreground border-transparent", dotColor: "bg-slate-500", pulsing: false },
    running: { label: "Running", classes: "bg-blue-500/10 text-blue-400 border-blue-500/20", dotColor: "bg-blue-500", pulsing: true },
    completed: { label: "Completed", classes: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", dotColor: "bg-emerald-500", pulsing: false },
    failed: { label: "Failed", classes: "bg-red-500/10 text-red-400 border-red-500/20", dotColor: "bg-red-500", pulsing: false },
};

/**
 * Recent audits list component for the dashboard.
 *
 * @param props - List of recent audits.
 */
export function RecentAudits({ audits }: RecentAuditsProps) {
    return (
        <div className="glass-card rounded-xl p-6 h-full flex flex-col">
            <h3 className="text-base font-semibold text-foreground mb-5 tracking-tight">
                Recent Audits
            </h3>
            <div className="space-y-3 flex-1">
                {audits.map((audit, index) => {
                    const config = statusConfig[audit.status];
                    return (
                        <div
                            key={audit.id}
                            className="group flex flex-col sm:flex-row sm:items-center gap-4 rounded-xl bg-slate-800/30 border border-transparent px-4 py-3.5 transition-all duration-200 hover:bg-slate-800/60 hover:border-slate-700 hover:shadow-md animate-fade-in"
                            style={{ animationDelay: `${index * 80}ms` }}
                        >
                            <div className="flex items-center gap-4 flex-1 min-w-0">
                                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-800/80 border border-slate-700/50 group-hover:scale-105 transition-transform duration-200 shadow-inner">
                                    <GitBranch className="h-4 w-4 text-slate-400 group-hover:text-primary transition-colors" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-semibold text-foreground truncate drop-shadow-sm">
                                        {audit.repository}
                                    </p>
                                    <div className="flex items-center gap-1.5 mt-1">
                                        <Clock className="h-3 w-3 text-slate-500" />
                                        <span className="text-xs text-slate-400 font-medium tracking-wide">
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
                            <div className="flex items-center justify-between sm:justify-end gap-4 shrink-0 mt-2 sm:mt-0">
                                {audit.status === "completed" && (
                                    <span className="text-xs font-medium text-slate-400 whitespace-nowrap">
                                        {audit.findings} findings
                                    </span>
                                )}
                                <span
                                    className={cn(
                                        "inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold shadow-sm whitespace-nowrap",
                                        config.classes
                                    )}
                                >
                                    <span className="relative flex h-2 w-2 shrink-0">
                                        {config.pulsing && (
                                            <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", config.dotColor)}></span>
                                        )}
                                        <span className={cn("relative inline-flex rounded-full h-2 w-2", config.dotColor)}></span>
                                    </span>
                                    {config.label}
                                </span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
