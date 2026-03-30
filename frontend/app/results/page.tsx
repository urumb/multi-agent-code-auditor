"use client";

import { useState, useEffect } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { FileSearch, Play, Download, FileJson, FileText } from "lucide-react";
import Link from "next/link";
import jsPDF from "jspdf";
import { toast } from "sonner";
import type { AuditResultResponse, FileAuditResult } from "@/lib/api";

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
                        className="flex items-center gap-2 rounded-lg bg-white/5 backdrop-blur-md border border-white/10 px-4 py-2.5 text-sm font-medium text-foreground hover:bg-white/10 hover:shadow-md transition-all duration-200"
                    >
                        <FileJson className="h-4 w-4 text-primary" />
                        Export JSON
                    </button>
                    <button
                        type="button"
                        onClick={exportAsPdf}
                        className="flex items-center gap-2 rounded-lg bg-white/5 backdrop-blur-md border border-white/10 px-4 py-2.5 text-sm font-medium text-foreground hover:bg-white/10 hover:shadow-md transition-all duration-200"
                    >
                        <Download className="h-4 w-4 text-emerald-400" />
                        Export PDF
                    </button>
                </div>
            </div>

            {/* Per-file report cards */}
            <div className="space-y-4">
                {result.results.map((file: FileAuditResult) => (
                    <div
                        key={file.file_path}
                        className="glass-card rounded-xl overflow-hidden"
                    >
                        {/* File header — clickable to expand/collapse */}
                        <button
                            type="button"
                            onClick={() => toggleFile(file.file_path)}
                            className="w-full flex items-center justify-between p-5 text-left hover:bg-white/5 transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                <FileText className="h-5 w-5 text-primary shrink-0" />
                                <span className="text-sm font-medium text-foreground font-mono">
                                    {file.file_path}
                                </span>
                            </div>
                            {file.error ? (
                                <span className="inline-flex items-center rounded-full bg-red-500/10 text-red-400 border border-red-500/20 px-2.5 py-0.5 text-xs font-medium">
                                    error
                                </span>
                            ) : (
                                <span className="inline-flex items-center rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 text-xs font-medium">
                                    report ready
                                </span>
                            )}
                        </button>

                        {/* Expanded report */}
                        {expandedFile === file.file_path && (
                            <div className="border-t border-white/10 p-5">
                                {file.error ? (
                                    <p className="text-sm text-red-400">
                                        {file.error}
                                    </p>
                                ) : (
                                    <pre className="text-sm text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed max-h-[600px] overflow-y-auto">
                                        {file.final_report ||
                                            "No report generated."}
                                    </pre>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
