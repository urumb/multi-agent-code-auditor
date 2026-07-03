"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { Finding, FindingCategory } from "@/types";
import { IssueCard } from "./issue-card";
import { EmptyState } from "@/components/ui/empty-state";
import type { Severity } from "@/types";
import { Flame, ShieldAlert, Bug } from "lucide-react";

/**
 * Props for the ResultTabs component.
 */
interface ResultTabsProps {
    /** All findings from the audit result. */
    findings: Finding[];
}

/** Tab configuration with icons and labels for severity filtering. */
const tabs: { severity: Severity; label: string; icon: React.ElementType; colorClass: string }[] = [
    { severity: "critical", label: "Critical", icon: Flame, colorClass: "text-red-500 border-red-500 bg-red-500/10" },
    { severity: "warning", label: "High / Warning", icon: ShieldAlert, colorClass: "text-yellow-500 border-yellow-500 bg-yellow-500/10" },
    { severity: "info", label: "Medium / Low", icon: Bug, colorClass: "text-primary border-primary bg-primary/10" },
];

/**
 * Tabbed results view filtering findings by severity.
 *
 * @param props - Findings data.
 */
export function ResultTabs({ findings }: ResultTabsProps) {
    const [activeTab, setActiveTab] = useState<Severity>("critical");

    const filteredFindings = findings.filter(
        (finding) => finding.severity === activeTab
    );

    const getSeverityCount = (severity: Severity) =>
        findings.filter((f) => f.severity === severity).length;

    return (
        <div>
            {/* Tab bar */}
            <div className="flex gap-2 mb-6 overflow-x-auto pb-1 border-b border-white/5">
                {tabs.map((tab) => {
                    const count = getSeverityCount(tab.severity);
                    const isActive = activeTab === tab.severity;
                    return (
                        <button
                            key={tab.severity}
                            type="button"
                            onClick={() => setActiveTab(tab.severity)}
                            className={cn(
                                "flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-all duration-200 whitespace-nowrap border-b-2",
                                isActive
                                    ? tab.colorClass.split(" ").filter(c => !c.startsWith("bg-")).join(" ") + " bg-white/5"
                                    : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5 border-transparent"
                            )}
                        >
                            <tab.icon className="h-4 w-4" />
                            {tab.label}
                            {count > 0 && (
                                <span
                                    className={cn(
                                        "flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-[10px] font-bold ml-1",
                                        isActive
                                            ? tab.colorClass.split(" ").find(c => c.startsWith("bg-")) + " " + tab.colorClass.split(" ").find(c => c.startsWith("text-"))
                                            : "bg-zinc-800 text-zinc-400"
                                    )}
                                >
                                    {count}
                                </span>
                            )}
                        </button>
                    );
                })}
            </div>

            {/* Findings list */}
            {filteredFindings.length === 0 ? (
                <EmptyState
                    title="No issues found"
                    description={`No ${activeTab} issues were detected in this audit.`}
                />
            ) : (
                <div className="space-y-4">
                    {filteredFindings.map((finding, index) => (
                        <IssueCard key={finding.id || index} finding={finding} index={index} />
                    ))}
                </div>
            )}
        </div>
    );
}
