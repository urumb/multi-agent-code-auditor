"use client";

import { useEffect, useState, use as usePromise } from "react";
import Link from "next/link";
import { ArrowLeft, Download, FileJson, FileText, AlertTriangle } from "lucide-react";
import { fetchAuditHistoryDetail, type AuditHistoryDetail } from "@/lib/api";
import { exportAuditAsJson, exportAuditAsPdf } from "@/lib/export";
import { AuditReportView } from "@/components/results/audit-report-view";
import { SeverityBadge } from "@/components/results/severity-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import type { Severity } from "@/types";

const STATUS_CLASSES: Record<string, string> = {
    completed: "bg-primary/10 text-primary border-primary/20",
    failed: "bg-red-500/10 text-red-400 border-red-500/20",
    running: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    pending: "bg-muted text-muted-foreground border-transparent",
};

export default function HistoryDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = usePromise(params);
    // Keyed on `id` so navigating between two audit ids remounts this
    // subtree — each id gets its own fresh loading/detail state instead of
    // needing an effect to reset state synchronously mid-lifecycle.
    return <HistoryDetailView key={id} id={id} />;
}

function HistoryDetailView({ id }: { id: string }) {
    const [detail, setDetail] = useState<AuditHistoryDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [expandedFile, setExpandedFile] = useState<string | null>(null);
    const [notFound, setNotFound] = useState(false);

    useEffect(() => {
        let mounted = true;
        fetchAuditHistoryDetail(id)
            .then((data) => {
                if (mounted) setDetail(data);
            })
            .catch(() => {
                if (mounted) setNotFound(true);
            })
            .finally(() => {
                if (mounted) setLoading(false);
            });
        return () => {
            mounted = false;
        };
    }, [id]);

    if (loading) {
        return (
            <div className="space-y-6">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-40 w-full" />
            </div>
        );
    }

    if (notFound || !detail) {
        return (
            <EmptyState
                icon={AlertTriangle}
                title="Audit not found"
                description="This audit may have been removed, or the id is invalid."
                action={
                    <Link
                        href="/history"
                        className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
                    >
                        Back to History
                    </Link>
                }
            />
        );
    }

    const overallMaxSeverity = detail.results.reduce<string>((acc, r) => {
        const order: Record<string, number> = { Critical: 3, High: 2, Medium: 1, Low: 0 };
        const cur = order[r.max_severity ?? "Low"] ?? 0;
        return cur > (order[acc] ?? 0) ? (r.max_severity ?? "Low") : acc;
    }, "Low");

    return (
        <div className="space-y-8">
            <div>
                <Link
                    href="/history"
                    className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-3"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Back to History
                </Link>
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-semibold text-foreground tracking-tight font-mono">
                            {detail.repository}
                        </h1>
                        <div className="flex items-center gap-3 mt-1.5">
                            <span
                                className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_CLASSES[detail.status] ?? STATUS_CLASSES.pending}`}
                            >
                                {detail.status}
                            </span>
                            <span className="text-sm text-muted-foreground">
                                {new Date(detail.created_at * 1000).toLocaleString()}
                            </span>
                            {detail.duration != null && (
                                <span className="text-sm text-muted-foreground">{detail.duration.toFixed(1)}s</span>
                            )}
                            {detail.results.length > 0 && (
                                <SeverityBadge severity={(overallMaxSeverity.toLowerCase() as Severity) || "low"} />
                            )}
                        </div>
                    </div>
                    {detail.results.length > 0 && (
                        <div className="flex items-center gap-3">
                            <button
                                type="button"
                                onClick={() =>
                                    exportAuditAsJson({ total_files: detail.total_files, results: detail.results })
                                }
                                className="flex items-center gap-2 rounded-md bg-secondary border border-border px-3.5 py-2 text-sm font-medium text-foreground hover:border-[#34363a] transition-colors"
                            >
                                <FileJson className="h-4 w-4 text-primary" />
                                Export JSON
                            </button>
                            <button
                                type="button"
                                onClick={() =>
                                    exportAuditAsPdf({ total_files: detail.total_files, results: detail.results })
                                }
                                className="flex items-center gap-2 rounded-md bg-secondary border border-border px-3.5 py-2 text-sm font-medium text-foreground hover:border-[#34363a] transition-colors"
                            >
                                <Download className="h-4 w-4 text-primary" />
                                Export PDF
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {(detail.files_skipped ?? 0) > 0 && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-400">
                    {detail.files_skipped} file(s) were not audited because the input exceeded the per-audit file limit.
                    The smallest files were audited first. Raise <code className="font-mono">MAX_FILES_PER_AUDIT</code> to include more.
                </div>
            )}

            {detail.error && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
                    {detail.error}
                </div>
            )}

            {detail.results.length === 0 ? (
                !detail.error && (
                    <p className="text-sm text-muted-foreground">This audit produced no file results.</p>
                )
            ) : (
                <div className="space-y-4">
                    {detail.results.map((file) => (
                        <div key={file.file_path} className="glass-card overflow-hidden">
                            <button
                                type="button"
                                onClick={() =>
                                    setExpandedFile((prev) => (prev === file.file_path ? null : file.file_path))
                                }
                                className="w-full flex items-center justify-between p-5 text-left hover:bg-secondary transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    <FileText className="h-5 w-5 text-primary shrink-0" />
                                    <span className="text-sm font-medium text-foreground font-mono">
                                        {file.file_path}
                                    </span>
                                    {file.max_severity && (
                                        <SeverityBadge severity={(file.max_severity.toLowerCase() as Severity) || "low"} />
                                    )}
                                </div>
                                {file.error ? (
                                    <span className="inline-flex items-center rounded-full bg-red-500/10 text-red-400 border border-red-500/20 px-2.5 py-0.5 text-xs font-medium">
                                        error
                                    </span>
                                ) : (
                                    <span className="inline-flex items-center rounded-full bg-primary/10 text-primary border border-primary/20 px-2.5 py-0.5 text-xs font-medium">
                                        report ready
                                    </span>
                                )}
                            </button>
                            {expandedFile === file.file_path && (
                                <div className="border-t border-border p-5">
                                    <AuditReportView file={file} />
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
