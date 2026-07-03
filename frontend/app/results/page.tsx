"use client";

import { useState, useEffect, useMemo } from "react";
import { EmptyState } from "@/components/ui/empty-state";
import { FileSearch, Play, Download, FileJson, ShieldAlert, Bug, Flame, CheckCircle, Clock, FileText } from "lucide-react";
import Link from "next/link";
import jsPDF from "jspdf";
import { toast } from "sonner";
import type { AuditResultResponse } from "@/lib/api";
import { ResultTabs } from "@/components/results/result-tabs";
import type { Finding } from "@/types";

export default function ResultsPage() {
    const [result, setResult] = useState<AuditResultResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        try {
            const stored = localStorage.getItem("latestAuditResult");
            if (stored) {
                setResult(JSON.parse(stored) as AuditResultResponse);
            }
        } catch {
        } finally {
            setLoading(false);
        }
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
            toast.success("JSON export complete");
        } catch {
            toast.error("Failed to export JSON");
        }
    };

    const exportAsPdf = () => {
        if (!result) return;
        try {
            const doc = new jsPDF();
            doc.setFontSize(20);
            doc.text("Code Audit Report", 14, 22);
            doc.setFontSize(12);
            doc.text(`Total Files Audited: ${result.total_files}`, 14, 32);

            let yPos = 50;
            result.results.forEach((file) => {
                if (yPos > 270) {
                    doc.addPage();
                    yPos = 20;
                }
                doc.setFontSize(14);
                doc.text(file.file_path, 14, yPos);
                yPos += 10;
                doc.setFontSize(10);

                let summary = "No issues found.";
                if (file.risk_score && file.risk_score > 0) summary = `Risk Score: ${file.risk_score.toFixed(1)}`;
                if (file.error) summary = `Error: ${file.error}`;

                doc.text(summary, 14, yPos);
                yPos += 15;
            });

            doc.save("audit-report.pdf");
            toast.success("PDF export complete");
        } catch {
            toast.error("Failed to export PDF");
        }
    };

    // Aggregate findings and stats
    const { allFindings, avgRiskScore, filesWithIssues, topRiskFiles, severityCounts, globalExecSummary } = useMemo(() => {
        if (!result) return { allFindings: [], avgRiskScore: 0, filesWithIssues: 0, topRiskFiles: [], severityCounts: { critical: 0, warning: 0, info: 0 }, globalExecSummary: "" };

        const findings: Finding[] = [];
        let totalScore = 0;
        let filesWithIssuesCount = 0;
        const trFilesMap = new Map();
        let execSummaryStr = "";

        result.results.forEach(file => {
            if (file.error) return;
            try {
                const data = JSON.parse(file.final_report || "{}");
                const fileFindings = (data.findings || []) as Finding[];

                if (fileFindings.length > 0) filesWithIssuesCount++;

                // Add file reference to findings
                const findingsWithFile = fileFindings.map(f => ({ ...f, file: file.file_path }));
                findings.push(...findingsWithFile);

                if (file.risk_score && file.risk_score > 0) {
                    totalScore += file.risk_score;
                }

                if (data["Executive Summary"] && !execSummaryStr) {
                     execSummaryStr = data["Executive Summary"]; // Grab first one as overall representation if global missing
                }

                if (data.top_risk_files) {
                     data.top_risk_files.forEach((trf: { file_path: string; risk_score: number }) => {
                         if (!trFilesMap.has(trf.file_path)) {
                             trFilesMap.set(trf.file_path, trf);
                         }
                     });
                }
            } catch { }
        });

        const counts = { critical: 0, warning: 0, info: 0 };
        findings.forEach(f => {
            if (f.severity === "critical") counts.critical++;
            else if (f.severity === "warning") counts.warning++;
            else counts.info++;
        });

        // Sort findings: Critical -> Warning -> Info
        const sortedFindings = [...findings].sort((a, b) => {
            const val: Record<string, number> = { critical: 3, warning: 2, info: 1 };
            const aVal = val[a.severity] ?? 0;
            const bVal = val[b.severity] ?? 0;
            return bVal - aVal;
        });

        const avg = filesWithIssuesCount > 0 ? (totalScore / filesWithIssuesCount) : 0;

        const trFiles = Array.from(trFilesMap.values()).sort((a,b) => (b.risk_score || 0) - (a.risk_score || 0));

        return {
            allFindings: sortedFindings,
            avgRiskScore: avg,
            filesWithIssues: filesWithIssuesCount,
            topRiskFiles: trFiles,
            severityCounts: counts,
            globalExecSummary: execSummaryStr || "Analysis completed successfully. Review detailed findings below."
        };
    }, [result]);

    if (loading) {
        return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading results...</div>;
    }

    if (!result) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
                <EmptyState
                    icon={FileSearch}
                    title="No audits yet"
                    description="Run your first scan to see results here."
                    action={
                        <Link href="/audit" className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-black hover:opacity-90 transition-opacity">
                            <Play className="h-4 w-4" /> Run Audit
                        </Link>
                    }
                />
            </div>
        );
    }

    // Determine Risk Color
    const getRiskColor = (score: number) => {
        if (score >= 7) return "text-red-500";
        if (score >= 4) return "text-yellow-500";
        return "text-primary"; // green
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-semibold text-foreground tracking-tight">Executive Summary</h1>
                </div>
                <div className="flex items-center gap-3">
                    <button onClick={exportAsJson} className="flex items-center gap-2 rounded-lg bg-[#151515] border border-white/5 px-4 py-2 text-sm font-medium hover:bg-white/5 transition-all">
                        <FileJson className="h-4 w-4 text-primary" /> JSON
                    </button>
                    <button onClick={exportAsPdf} className="flex items-center gap-2 rounded-lg bg-[#151515] border border-white/5 px-4 py-2 text-sm font-medium hover:bg-white/5 transition-all">
                        <Download className="h-4 w-4 text-primary" /> PDF
                    </button>
                </div>
            </div>

            {/* Top row: Stats and Health */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                {/* Overall Score */}
                <div className="glass-card p-6 flex flex-col justify-center items-center">
                    <p className="text-sm text-zinc-400 mb-2">Overall Risk Score</p>
                    <p className={`text-6xl font-bold ${getRiskColor(avgRiskScore)} drop-shadow-sm`}>
                        {avgRiskScore.toFixed(1)}
                    </p>
                    <p className="text-xs text-zinc-500 mt-2">/ 10.0</p>
                </div>

                {/* Severity Breakdown */}
                <div className="glass-card p-6 md:col-span-3 grid grid-cols-3 gap-4">
                    <div className="flex flex-col items-center justify-center border-r border-white/5">
                        <Flame className="h-6 w-6 text-red-500 mb-2" />
                        <span className="text-3xl font-bold text-foreground">{severityCounts.critical}</span>
                        <span className="text-xs text-zinc-400">Critical Issues</span>
                    </div>
                    <div className="flex flex-col items-center justify-center border-r border-white/5">
                        <ShieldAlert className="h-6 w-6 text-yellow-500 mb-2" />
                        <span className="text-3xl font-bold text-foreground">{severityCounts.warning}</span>
                        <span className="text-xs text-zinc-400">Warnings</span>
                    </div>
                    <div className="flex flex-col items-center justify-center">
                        <Bug className="h-6 w-6 text-zinc-400 mb-2" />
                        <span className="text-3xl font-bold text-foreground">{severityCounts.info}</span>
                        <span className="text-xs text-zinc-400">Info / Suggestions</span>
                    </div>
                </div>
            </div>

            {/* Overview & Summary row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="glass-card p-6 lg:col-span-2">
                    <h3 className="text-lg font-semibold mb-4 text-foreground">Analysis Overview</h3>
                    <p className="text-sm text-zinc-400 leading-relaxed">
                        {globalExecSummary}
                    </p>
                </div>

                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-4 text-foreground">Repository Stats</h3>
                    <ul className="space-y-4 text-sm">
                        <li className="flex justify-between items-center">
                            <span className="text-zinc-400 flex items-center gap-2"><FileText className="h-4 w-4"/> Files Scanned</span>
                            <span className="font-mono">{result.total_files}</span>
                        </li>
                        <li className="flex justify-between items-center">
                            <span className="text-zinc-400 flex items-center gap-2"><CheckCircle className="h-4 w-4 text-red-500"/> Files with Issues</span>
                            <span className="font-mono text-red-400">{filesWithIssues}</span>
                        </li>
                        <li className="flex justify-between items-center">
                            <span className="text-zinc-400 flex items-center gap-2"><Clock className="h-4 w-4"/> Generated</span>
                            <span className="font-mono text-xs">Just now</span>
                        </li>
                    </ul>
                </div>
            </div>

            {/* Recommendations (Actionable checklist) */}
            {allFindings.filter((f) => f.suggestedFix).length > 0 && (
                <div className="glass-card p-6 border-primary/20 bg-primary/5">
                    <h3 className="text-lg font-semibold mb-4 text-primary flex items-center gap-2">
                        <CheckCircle className="h-5 w-5" />
                        Recommendations
                    </h3>
                    <ul className="space-y-3">
                        {allFindings
                            .filter((f) => f.suggestedFix && f.severity === "critical")
                            .slice(0, 3)
                            .map((f, i) => (
                                <li key={`rec-${i}`} className="flex items-start gap-3">
                                    <div className="w-1.5 h-1.5 rounded-full bg-red-500 mt-2 shrink-0" />
                                    <div>
                                        <p className="text-sm font-medium text-foreground">{f.title}</p>
                                        <p className="text-xs text-zinc-400 mt-1">{f.file}:{f.line}</p>
                                    </div>
                                </li>
                            ))}
                        {allFindings
                            .filter((f) => f.suggestedFix && f.severity === "warning")
                            .slice(0, 2)
                            .map((f, i) => (
                                <li key={`rec-warn-${i}`} className="flex items-start gap-3">
                                    <div className="w-1.5 h-1.5 rounded-full bg-yellow-500 mt-2 shrink-0" />
                                    <div>
                                        <p className="text-sm font-medium text-foreground">{f.title}</p>
                                        <p className="text-xs text-zinc-400 mt-1">{f.file}:{f.line}</p>
                                    </div>
                                </li>
                            ))}
                    </ul>
                </div>
            )}

            {/* Top Risk Files */}
            {topRiskFiles.length > 0 && (
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold mb-4 text-foreground">Top Risk Files</h3>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-[#050505] border-b border-white/5">
                                <tr>
                                    <th className="px-4 py-3 font-medium text-zinc-400">File Path</th>
                                    <th className="px-4 py-3 font-medium text-zinc-400 text-right">Risk Score</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 bg-[#0a0a0a]">
                                {topRiskFiles.map((f, i) => (
                                    <tr key={i} className="hover:bg-[#151515] transition-colors">
                                        <td className="px-4 py-3 font-mono text-primary text-xs">{f.file_path}</td>
                                        <td className={`px-4 py-3 font-mono text-right ${getRiskColor(f.risk_score)}`}>{f.risk_score?.toFixed(1) || "-"}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Detailed Findings Tabs */}
            {allFindings.length > 0 && (
                <div className="pt-4">
                    <h2 className="text-xl font-semibold text-foreground mb-4">Detailed Findings</h2>
                    <ResultTabs findings={allFindings} />
                </div>
            )}

            {/* Raw Report Details (Collapsible fallback for errors) */}
            <div className="mt-8 pt-8 border-t border-white/5">
                 <details className="group">
                     <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-300 transition-colors list-none flex items-center gap-2">
                         <span>View Raw Logs</span>
                     </summary>
                     <div className="mt-4 p-4 bg-[#050505] border border-white/5 rounded-xl max-h-96 overflow-y-auto">
                        {result.results.map((r, idx) => (
                            <div key={idx} className="mb-4">
                                <p className="text-xs text-primary font-mono font-bold mb-1">{r.file_path}</p>
                                {r.error ? (
                                    <p className="text-xs text-red-500">{r.error}</p>
                                ) : (
                                    <p className="text-xs text-zinc-600 line-clamp-2 italic">Parsed successfully.</p>
                                )}
                            </div>
                        ))}
                     </div>
                 </details>
            </div>
        </div>
    );
}
