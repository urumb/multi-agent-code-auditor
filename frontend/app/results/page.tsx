"use client";

import { useState, useEffect } from "react";
import { ResultTabs } from "@/components/results/result-tabs";
import { IssueCardSkeleton } from "@/components/results/issue-card-skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { fetchAuditResult } from "@/lib/api";
import type { AuditResult } from "@/types";
import { FileSearch, Play, Download, FileJson } from "lucide-react";
import Link from "next/link";
import jsPDF from "jspdf";
import { toast } from "sonner";

/**
 * Results page displaying categorized audit findings.
 */
export default function ResultsPage() {
    const [result, setResult] = useState<AuditResult | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadResults() {
            try {
                const data = await fetchAuditResult("latest");
                setResult(data);
            } finally {
                setLoading(false);
            }
        }

        loadResults();
    }, []);

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

            // Title
            doc.setFontSize(22);
            doc.text("Audit Report", 14, yPos);
            yPos += 10;

            // Metadata
            doc.setFontSize(12);
            doc.text(`Project: ${result.repository}`, 14, yPos);
            yPos += 8;
            doc.text(`Date: ${new Date().toLocaleDateString()}`, 14, yPos);
            yPos += 8;
            doc.text(`Status: ${result.status.toUpperCase()}`, 14, yPos);
            yPos += 15;

            // Summary
            doc.setFontSize(14);
            doc.text("Summary of Findings", 14, yPos);
            yPos += 8;
            doc.setFontSize(10);

            // Simple word wrap for summary
            const splitSummary = doc.splitTextToSize(result.summary, pageWidth - 28);
            doc.text(splitSummary, 14, yPos);
            yPos += (splitSummary.length * 6) + 10;

            // Group findings by severity
            const severities: ("critical" | "warning" | "info")[] = ["critical", "warning", "info"];

            severities.forEach((severity) => {
                const items = result.findings.filter(f => f.severity === severity);
                if (items.length > 0) {
                    if (yPos > doc.internal.pageSize.getHeight() - 40) {
                        doc.addPage();
                        yPos = 20;
                    }

                    doc.setFontSize(14);
                    doc.text(`${severity.charAt(0).toUpperCase() + severity.slice(1)} Issues (${items.length})`, 14, yPos);
                    yPos += 8;

                    items.forEach((item, index) => {
                        if (yPos > doc.internal.pageSize.getHeight() - 50) {
                            doc.addPage();
                            yPos = 20;
                        }

                        doc.setFontSize(11);
                        doc.text(`${index + 1}. ${item.title}`, 14, yPos);
                        yPos += 6;

                        doc.setFontSize(9);
                        doc.text(`File: ${item.file}:${item.line}  |  Category: ${item.category}`, 18, yPos);
                        yPos += 6;

                        const splitDesc = doc.splitTextToSize(`Description: ${item.description}`, pageWidth - 32);
                        doc.text(splitDesc, 18, yPos);
                        yPos += (splitDesc.length * 5) + 4;

                        const splitFix = doc.splitTextToSize(`Suggested Fix: ${item.suggestedFix.substring(0, 150)}...`, pageWidth - 32);
                        doc.text(splitFix, 18, yPos);
                        yPos += (splitFix.length * 5) + 10;
                    });
                }
            });

            doc.save("audit-report.pdf");
            toast.success("PDF report exported successfully.");
        } catch (e) {
            console.error(e);
            toast.error("Failed to generate PDF report.");
        }
    };

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
                            {result
                                ? `Audit findings for ${result.repository}`
                                : "View your latest audit findings."}
                        </p>
                        {result && (
                            <div className="flex items-center gap-2">
                                <span className="inline-flex items-center gap-1.5 rounded-full border bg-emerald-500/10 text-emerald-400 border-emerald-500/20 px-2.5 py-0.5 text-xs font-medium">
                                    {result.status}
                                </span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Export Actions */}
                {result && result.findings.length > 0 && (
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
                )}
            </div>

            {/* Content */}
            {loading ? (
                <div className="space-y-4">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <IssueCardSkeleton key={i} />
                    ))}
                </div>
            ) : result && result.findings.length > 0 ? (
                <>
                    {/* Summary bar */}
                    <div className="glass-card rounded-xl p-4">
                        <p className="text-sm text-muted-foreground">{result.summary}</p>
                    </div>
                    <ResultTabs findings={result.findings} />
                </>
            ) : (
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
            )}
        </div>
    );
}
