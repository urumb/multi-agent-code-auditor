"use client";

import { useState, useEffect } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { FileSearch, Play, Download, FileJson, FileText } from "lucide-react";
import Link from "next/link";
import type { AuditResultResponse, FileAuditResult } from "@/lib/api";
import { exportAuditAsJson, exportAuditAsPdf } from "@/lib/export";
import { AuditReportView } from "@/components/results/audit-report-view";
import { SeverityBadge } from "@/components/results/severity-badge";
import type { Severity } from "@/types";

/**
 * Results page displaying per-file audit reports from the backend.
 * Reads the latest audit result from localStorage (set by useAudit hook).
 */
export default function ResultsPage() {
    const [result, setResult] = useState<AuditResultResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [expandedFile, setExpandedFile] = useState<string | null>(null);

    useEffect(() => {
        try {
            const stored = localStorage.getItem("latestAuditResult");
            if (stored) {
                setResult(JSON.parse(stored) as AuditResultResponse);
            }
        } catch {
            // Corrupted localStorage — ignore
        } finally {
            setLoading(false);
        }
    }, []);

    const toggleFile = (filePath: string) => {
        setExpandedFile((prev) => (prev === filePath ? null : filePath));
    };

    /** Renders the loading skeleton. */
    if (loading) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                        Results
                    </h1>
                    <p className="text-sm text-muted-foreground mt-1">
                        Loading results...
                    </p>
                </div>
                <div className="space-y-4">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <div
                            key={i}
                            className="glass-card p-6 animate-pulse"
                        >
                            <div className="h-4 w-1/3 bg-muted/50 rounded mb-3" />
                            <div className="h-3 w-full bg-muted/30 rounded mb-2" />
                            <div className="h-3 w-2/3 bg-muted/30 rounded" />
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    /** Renders empty state if no results. */
    if (!result || result.results.length === 0) {
        return (
            <div className="space-y-8">
                <div>
                    <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                        Results
                    </h1>
                    <p className="text-sm text-muted-foreground mt-1">
                        View your latest audit findings.
                    </p>
                </div>
                <EmptyState
                    icon={FileSearch}
                    title="No audits yet"
                    description="Run your first scan to see results here."
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
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Page header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                        Results
                    </h1>
                    <div className="flex items-center gap-3 mt-1">
                        <p className="text-sm text-muted-foreground">
                            {result.total_files} file(s) audited
                        </p>
                        <span className="inline-flex items-center gap-1.5 rounded-full border bg-primary/10 text-primary border-primary/20 px-2.5 py-0.5 text-xs font-medium">
                            completed
                        </span>
                    </div>
                </div>

                {/* Export Actions */}
                <div className="flex items-center gap-3">
                    <button
                        type="button"
                        onClick={() => exportAuditAsJson(result)}
                        className="flex items-center gap-2 rounded-md bg-secondary border border-border px-3.5 py-2 text-sm font-medium text-foreground hover:border-[#34363a] transition-colors"
                    >
                        <FileJson className="h-4 w-4 text-primary" />
                        Export JSON
                    </button>
                    <button
                        type="button"
                        onClick={() => exportAuditAsPdf(result)}
                        className="flex items-center gap-2 rounded-md bg-secondary border border-border px-3.5 py-2 text-sm font-medium text-foreground hover:border-[#34363a] transition-colors"
                    >
                        <Download className="h-4 w-4 text-primary" />
                        Export PDF
                    </button>
                </div>
            </div>

            {(result.files_skipped ?? 0) > 0 && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-400">
                    {result.files_skipped} file(s) were not audited because the input exceeded the per-audit file limit.
                    The smallest files were audited first. Raise <code className="font-mono">MAX_FILES_PER_AUDIT</code> to include more.
                </div>
            )}

            {/* Per-file report cards */}
            <div className="space-y-4">
                {result.results.map((file: FileAuditResult) => (
                    <div
                        key={file.file_path}
                        className="glass-card overflow-hidden"
                    >
                        {/* File header — clickable to expand/collapse */}
                        <button
                            type="button"
                            onClick={() => toggleFile(file.file_path)}
                            className="w-full flex items-center justify-between p-5 text-left hover:bg-secondary transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                <FileText className="h-5 w-5 text-primary shrink-0" />
                                <span className="text-sm font-medium text-foreground font-mono">
                                    {file.file_path}
                                </span>
                                {file.max_severity && (
                                    <SeverityBadge
                                        severity={(file.max_severity.toLowerCase() as Severity) || "low"}
                                    />
                                )}
                                {file.risk_score !== undefined && (
                                    <span className="text-xs text-muted-foreground">
                                        risk {file.risk_score.toFixed(1)}
                                    </span>
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

                        {/* Expanded report */}
                        {expandedFile === file.file_path && (
                            <div className="border-t border-border p-5">
                                <AuditReportView file={file} />
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
