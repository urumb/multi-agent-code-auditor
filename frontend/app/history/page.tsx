"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { History, Play, GitBranch, Clock, ChevronLeft, ChevronRight } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SeverityBadge } from "@/components/results/severity-badge";
import { fetchAuditHistory, type AuditHistoryEntry } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Severity } from "@/types";

const PAGE_SIZE = 20;

const STATUS_CLASSES: Record<string, string> = {
    completed: "bg-primary/10 text-primary border-primary/20",
    failed: "bg-red-500/10 text-red-400 border-red-500/20",
    running: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    pending: "bg-muted text-muted-foreground border-transparent",
};

/**
 * Full audit history — every past run, persisted server-side, paginated.
 * Each row links to its full report.
 */
export default function HistoryPage() {
    const [entries, setEntries] = useState<AuditHistoryEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [hasMore, setHasMore] = useState(false);

    const load = useCallback(async (pageIndex: number) => {
        setLoading(true);
        try {
            const data = await fetchAuditHistory(PAGE_SIZE + 1, pageIndex * PAGE_SIZE);
            setHasMore(data.length > PAGE_SIZE);
            setEntries(data.slice(0, PAGE_SIZE));
        } catch {
            setEntries([]);
            setHasMore(false);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load(page);
    }, [page, load]);

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-2xl font-semibold text-foreground tracking-tight">History</h1>
                <p className="text-sm text-muted-foreground mt-1">
                    Every audit that has run, persisted across restarts.
                </p>
            </div>

            {loading ? (
                <div className="space-y-2">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <Skeleton key={i} className="h-14 w-full" />
                    ))}
                </div>
            ) : entries.length === 0 ? (
                <EmptyState
                    icon={History}
                    title="No audit history yet"
                    description="Runs you start will show up here, even after a restart."
                    action={
                        <Link
                            href="/audit"
                            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
                        >
                            <Play className="h-4 w-4" />
                            Run Audit
                        </Link>
                    }
                />
            ) : (
                <>
                    <div className="glass-card divide-y divide-border overflow-hidden">
                        {entries.map((entry) => (
                            <Link
                                key={entry.id}
                                href={`/history/${entry.id}`}
                                className="flex items-center gap-4 px-5 py-3.5 hover:bg-secondary transition-colors"
                            >
                                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-secondary border border-border">
                                    <GitBranch className="h-4 w-4 text-muted-foreground" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-foreground truncate">
                                        {entry.repository}
                                    </p>
                                    <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground">
                                        <Clock className="h-3 w-3" />
                                        {new Date(entry.date).toLocaleString()}
                                        <span className="text-muted-foreground/60">·</span>
                                        {entry.input_type}
                                        {entry.duration != null && (
                                            <>
                                                <span className="text-muted-foreground/60">·</span>
                                                {entry.duration.toFixed(1)}s
                                            </>
                                        )}
                                    </div>
                                </div>
                                {entry.status === "completed" && entry.files_errored === 0 && (
                                    <SeverityBadge severity={(entry.max_severity?.toLowerCase() as Severity) || "low"} />
                                )}
                                <span className="text-xs text-muted-foreground whitespace-nowrap w-28 text-right">
                                    {entry.files_errored > 0
                                        ? `${entry.files_errored} file(s) errored`
                                        : `${entry.findings} finding${entry.findings === 1 ? "" : "s"}`}
                                </span>
                                <span
                                    className={cn(
                                        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
                                        entry.status === "completed" && entry.files_errored > 0
                                            ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
                                            : STATUS_CLASSES[entry.status] ?? STATUS_CLASSES.pending
                                    )}
                                >
                                    {entry.status === "completed" && entry.files_errored > 0 ? "errored" : entry.status}
                                </span>
                            </Link>
                        ))}
                    </div>

                    <div className="flex items-center justify-between">
                        <button
                            type="button"
                            disabled={page === 0}
                            onClick={() => setPage((p) => Math.max(0, p - 1))}
                            className="flex items-center gap-1.5 rounded-md border border-border bg-secondary px-3 py-1.5 text-sm text-foreground disabled:opacity-40 disabled:cursor-not-allowed hover:border-[#34363a] transition-colors"
                        >
                            <ChevronLeft className="h-4 w-4" />
                            Newer
                        </button>
                        <span className="text-xs text-muted-foreground">Page {page + 1}</span>
                        <button
                            type="button"
                            disabled={!hasMore}
                            onClick={() => setPage((p) => p + 1)}
                            className="flex items-center gap-1.5 rounded-md border border-border bg-secondary px-3 py-1.5 text-sm text-foreground disabled:opacity-40 disabled:cursor-not-allowed hover:border-[#34363a] transition-colors"
                        >
                            Older
                            <ChevronRight className="h-4 w-4" />
                        </button>
                    </div>
                </>
            )}
        </div>
    );
}
