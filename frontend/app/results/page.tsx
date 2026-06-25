"use client";

import { useState, useEffect } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { FileSearch, Play, Download, FileJson, FileText } from "lucide-react";
import Link from "next/link";
import jsPDF from "jspdf";
import { toast } from "sonner";
import type { AuditResultResponse, FileAuditResult } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ResultTabs } from "@/components/results/result-tabs";

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

    const exportAsJson = () => {
        if (!result) return;
        try {
            const dataStr = JSON.stringify(result, null, 2);
            const blob = new Blob([dataStr], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = "audit-report.json";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            toast.success("JSON report exported successfully.");
        } catch {
            toast.error("Failed to export JSON report.");
        }
    };

    const exportAsPdf = () => {
        if (!result) return;
        try {
            const doc = new jsPDF();
            const pageWidth = doc.internal.pageSize.getWidth();
            let yPos = 20;

            doc.setFontSize(22);
            doc.text("Audit Report", 14, yPos);
            yPos += 10;

            doc.setFontSize(12);
            doc.text(`Total Files: ${result.total_files}`, 14, yPos);
            yPos += 8;
            doc.text(`Date: ${new Date().toLocaleDateString()}`, 14, yPos);
            yPos += 15;

            result.results.forEach((file) => {
                if (yPos > doc.internal.pageSize.getHeight() - 40) {
                    doc.addPage();
                    yPos = 20;
                }

                doc.setFontSize(14);
                doc.text(`File: ${file.file_path}`, 14, yPos);
                yPos += 8;

                if (file.error) {
                    doc.setFontSize(10);
                    doc.text(`Error: ${file.error}`, 14, yPos);
                    yPos += 12;
                } else {
                    doc.setFontSize(10);
                    const lines = doc.splitTextToSize(
                        file.final_report || "No report generated.",
                        pageWidth - 28
                    );
                    doc.text(lines, 14, yPos);
                    yPos += lines.length * 5 + 10;
                }
            });

            doc.save("audit-report.pdf");
            toast.success("PDF report exported successfully.");
        } catch (e) {
            console.error(e);
            toast.error("Failed to generate PDF report.");
        }
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
                            className="glass-card rounded-xl p-6 animate-pulse"
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
                        <span className="inline-flex items-center gap-1.5 rounded-full border bg-emerald-500/10 text-emerald-400 border-emerald-500/20 px-2.5 py-0.5 text-xs font-medium">
                            completed
                        </span>
                    </div>
                </div>

                {/* Export Actions */}
                <div className="flex items-center gap-3">
                    <button
                        type="button"
                        onClick={exportAsJson}
                        className="flex items-center gap-2 rounded-md bg-secondary/50 border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary hover:shadow-sm transition-colors duration-200"
                    >
                        <FileJson className="h-4 w-4 text-primary" />
                        Export JSON
                    </button>
                    <button
                        type="button"
                        onClick={exportAsPdf}
                        className="flex items-center gap-2 rounded-md bg-secondary/50 border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary hover:shadow-sm transition-colors duration-200"
                    >
                        <Download className="h-4 w-4 text-primary" />
                        Export PDF
                    </button>
                </div>
            </div>

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
                            className="w-full flex items-center justify-between p-4 text-left hover:bg-secondary/30 transition-colors border-b border-transparent data-[state=open]:border-border"
                            data-state={expandedFile === file.file_path ? "open" : "closed"}
                        >
                            <div className="flex items-center gap-3">
                                <FileText className="h-4 w-4 text-primary shrink-0" />
                                <span className="text-sm font-medium text-foreground font-mono">
                                    {file.file_path}
                                </span>
                                {file.risk_score !== undefined && file.risk_score > 0 && (
                                    <span className={cn(
                                        "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider border",
                                        file.risk_score >= 7 ? "bg-destructive/10 text-destructive border-destructive/20" :
                                        file.risk_score >= 4 ? "bg-amber-500/10 text-amber-500 border-amber-500/20" :
                                        "bg-primary/10 text-primary border-primary/20"
                                    )}>
                                        Risk: {file.risk_score.toFixed(1)}
                                    </span>
                                )}
                            </div>
                            {file.error ? (
                                <span className="inline-flex items-center rounded-full bg-destructive/10 text-destructive border border-destructive/20 px-2.5 py-0.5 text-[10px] uppercase font-bold tracking-wider">
                                    Error
                                </span>
                            ) : (
                                <span className="inline-flex items-center rounded-full bg-primary/10 text-primary border border-primary/20 px-2.5 py-0.5 text-[10px] uppercase font-bold tracking-wider">
                                    Ready
                                </span>
                            )}
                        </button>

                        {/* Expanded report */}
                        {expandedFile === file.file_path && (
                            <div className="border-t border-border p-6 bg-background">
                                {file.error ? (
                                    <p className="text-sm text-destructive">
                                        {file.error}
                                    </p>
                                ) : (
                                        (() => {
                                            try {
                                                const data = JSON.parse(file.final_report || "{}");
                                                const findings = data.findings || [];
                                                const execSummary = data["Executive Summary"] || "";
                                                const findingsSummary = data["Findings Summary"] || "";
                                                const topRiskFiles = data["top_risk_files"] || [];

                                                return (
                                                    <div className="space-y-8">
                                                        {topRiskFiles.length > 0 && (
                                                            <div className="bg-destructive/5 border border-destructive/20 p-5 rounded-md">
                                                                <h4 className="text-xs uppercase font-bold tracking-wider text-destructive mb-3">Top Risk Files</h4>
                                                                <ul className="space-y-1.5">
                                                                    {topRiskFiles.map((trf: { file_path: string; risk_score?: number }) => (
                                                                        <li key={trf.file_path} className="flex justify-between items-center text-sm">
                                                                            <span className="font-mono text-muted-foreground">{trf.file_path}</span>
                                                                            <span className="font-medium text-destructive">{trf.risk_score?.toFixed(1)}</span>
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                        )}
                                                        {(execSummary || findingsSummary) && (
                                                          <div className="grid md:grid-cols-2 gap-6 bg-secondary/20 border border-border p-6 rounded-md">
                                                              {execSummary && (
                                                                <div>
                                                                    <h4 className="text-xs uppercase font-bold tracking-wider text-muted-foreground mb-2">Executive Summary</h4>
                                                                    <p className="text-sm text-foreground leading-relaxed">{execSummary}</p>
                                                                </div>
                                                              )}
                                                              {findingsSummary && (
                                                                <div>
                                                                    <h4 className="text-xs uppercase font-bold tracking-wider text-muted-foreground mb-2">Findings Summary</h4>
                                                                    <p className="text-sm text-foreground leading-relaxed">{findingsSummary}</p>
                                                                </div>
                                                              )}
                                                          </div>
                                                        )}

                                                        {findings.length > 0 && (
                                                            <div>
                                                                <h4 className="text-xs uppercase font-bold tracking-wider text-muted-foreground mb-4">Detailed Findings</h4>
                                                                <ResultTabs findings={findings} />
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            } catch {
                                                return (
                                                    <pre className="text-sm text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed max-h-[600px] overflow-y-auto p-4 bg-secondary/30 rounded-md border border-border">
                                                        {file.final_report ||
                                                            "No report generated."}
                                                    </pre>
                                                );
                                            }
                                        })()
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
