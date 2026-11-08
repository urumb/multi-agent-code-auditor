"use client";

import type { FileAuditResult } from "@/lib/api";
import { mapFindings } from "@/lib/findings";
import { ResultTabs } from "./result-tabs";

interface TopRiskFile {
    file_path: string;
    risk_score?: number;
}

interface ParsedReport {
    "Executive Summary"?: string;
    "Findings Summary"?: string;
    top_risk_files?: TopRiskFile[];
    findings?: import("@/lib/findings").RawFinding[];
}

/**
 * Renders one file's parsed audit report — executive summary, findings
 * summary, top-risk files, and the tabbed findings list. Shared between the
 * Results page (latest run) and History detail pages (any past run) so both
 * paths get identical, correctly-mapped structured findings.
 */
export function AuditReportView({ file }: { file: FileAuditResult }) {
    if (file.error) {
        return <p className="text-sm text-red-400">{file.error}</p>;
    }

    let data: ParsedReport;
    try {
        data = JSON.parse(file.final_report || "{}") as ParsedReport;
    } catch {
        return (
            <pre className="text-sm text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed max-h-[600px] overflow-y-auto">
                {file.final_report || "No report generated."}
            </pre>
        );
    }

    const findings = mapFindings(data.findings, file.file_path);
    const execSummary = data["Executive Summary"] || "";
    const findingsSummary = data["Findings Summary"] || "";
    const topRiskFiles = data.top_risk_files || [];

    return (
        <div className="space-y-6">
            {topRiskFiles.length > 0 && (
                <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-lg">
                    <h4 className="text-sm font-semibold text-red-400 mb-2">Top Risk Files</h4>
                    <ul className="list-disc list-inside text-sm text-muted-foreground">
                        {topRiskFiles.map((trf) => (
                            <li key={trf.file_path}>
                                {trf.file_path} — Score: {trf.risk_score?.toFixed(1)}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            <div>
                <h4 className="text-sm font-semibold text-foreground mb-2">Executive Summary</h4>
                <p className="text-sm text-muted-foreground">{execSummary || "—"}</p>
            </div>
            <div>
                <h4 className="text-sm font-semibold text-foreground mb-2">Findings Summary</h4>
                <p className="text-sm text-muted-foreground">{findingsSummary || "—"}</p>
            </div>

            {findings.length > 0 ? (
                <div>
                    <h4 className="text-sm font-semibold text-foreground mb-4 mt-6">Detailed Findings</h4>
                    <ResultTabs findings={findings} />
                </div>
            ) : (
                <p className="text-sm text-muted-foreground">No issues were detected in this file.</p>
            )}
        </div>
    );
}
