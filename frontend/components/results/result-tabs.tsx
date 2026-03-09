"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { Finding, FindingCategory } from "@/types";
import { IssueCard } from "./issue-card";
import { EmptyState } from "@/components/ui/empty-state";
import { Shield, Gauge, Code, Lightbulb } from "lucide-react";

/**
 * Props for the ResultTabs component.
 */
interface ResultTabsProps {
    /** All findings from the audit result. */
    findings: Finding[];
}

/** Tab configuration with icons and labels. */
const tabs: { category: FindingCategory; label: string; icon: React.ElementType }[] = [
    { category: "security", label: "Security", icon: Shield },
    { category: "code-quality", label: "Code Quality", icon: Code },
    { category: "performance", label: "Performance", icon: Gauge },
    { category: "suggestion", label: "Suggestions", icon: Lightbulb },
];

/**
 * Tabbed results view filtering findings by category.
 *
 * @param props - Findings data.
 */
export function ResultTabs({ findings }: ResultTabsProps) {
    const [activeTab, setActiveTab] = useState<FindingCategory>("security");

    const filteredFindings = findings.filter(
        (finding) => finding.category === activeTab
    );

    const getCategoryCount = (category: FindingCategory) =>
        findings.filter((f) => f.category === category).length;

    return (
        <div>
            {/* Tab bar */}
            <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
                {tabs.map((tab) => {
                    const count = getCategoryCount(tab.category);
                    return (
                        <button
                            key={tab.category}
                            type="button"
                            onClick={() => setActiveTab(tab.category)}
                            className={cn(
                                "flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200 whitespace-nowrap",
                                activeTab === tab.category
                                    ? "bg-primary/10 text-primary border border-primary/20"
                                    : "bg-muted/30 text-muted-foreground hover:bg-muted/50 hover:text-foreground border border-transparent"
                            )}
                        >
                            <tab.icon className="h-4 w-4" />
                            {tab.label}
                            {count > 0 && (
                                <span
                                    className={cn(
                                        "flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-[10px] font-bold",
                                        activeTab === tab.category
                                            ? "bg-primary/20 text-primary"
                                            : "bg-muted text-muted-foreground"
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
                        <IssueCard key={finding.id} finding={finding} index={index} />
                    ))}
                </div>
            )}
        </div>
    );
}
