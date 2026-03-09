"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { Finding } from "@/types";
import { SeverityBadge } from "./severity-badge";
import { CodeViewer } from "./code-viewer";
import { Copy, Check, FileCode, ChevronDown, ChevronUp } from "lucide-react";
import { toast } from "sonner";

/**
 * Props for the IssueCard component.
 */
interface IssueCardProps {
    /** Finding data to display. */
    finding: Finding;
    /** Stagger delay index for animation. */
    index?: number;
}

/**
 * Issue card displaying a single audit finding with severity, location,
 * description, code snippet, and "Copy Fix" functionality.
 *
 * @param props - Finding data and display configuration.
 */
export function IssueCard({ finding, index = 0 }: IssueCardProps) {
    const [expanded, setExpanded] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopyFix = async () => {
        try {
            await navigator.clipboard.writeText(finding.suggestedFix);
            setCopied(true);
            toast.success("Fix suggestion copied to clipboard");
            setTimeout(() => setCopied(false), 2000);
        } catch {
            toast.error("Failed to copy to clipboard");
        }
    };

    return (
        <div
            className={cn(
                "glass-card overflow-hidden animate-fade-in group",
                finding.severity === "critical"
                    ? "border-red-500/40 shadow-[0_4px_15px_-3px_rgba(239,68,68,0.1)] hover:border-red-500/60"
                    : finding.severity === "warning"
                        ? "border-yellow-400/40 shadow-[0_4px_15px_-3px_rgba(250,204,21,0.1)] hover:border-yellow-400/60"
                        : "hover:border-primary/20"
            )}
            style={{ animationDelay: `${index * 100}ms` }}
        >
            {/* Header */}
            <div className="p-4">
                <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                            <SeverityBadge severity={finding.severity} />
                            <span className="text-xs text-muted-foreground">
                                {finding.agent}
                            </span>
                        </div>
                        <h4 className="text-sm font-semibold text-foreground">
                            {finding.title}
                        </h4>
                        <div className="flex items-center gap-1.5 mt-1.5">
                            <FileCode className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground font-mono">
                                {finding.file}:{finding.line}
                            </span>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={() => setExpanded(!expanded)}
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted/30 text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
                    >
                        {expanded ? (
                            <ChevronUp className="h-4 w-4" />
                        ) : (
                            <ChevronDown className="h-4 w-4" />
                        )}
                    </button>
                </div>

                <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                    {finding.description}
                </p>
            </div>

            {/* Expanded content */}
            {expanded && (
                <div className="border-t border-border px-4 py-4 space-y-4">
                    {/* Original code */}
                    <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">
                            Current Code
                        </p>
                        <CodeViewer
                            code={finding.codeSnippet}
                            language="python"
                            highlightLine={1}
                        />
                    </div>

                    {/* Suggested fix */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <p className="text-xs font-medium text-emerald-400 uppercase tracking-wider">
                                Suggested Fix
                            </p>
                            <button
                                type="button"
                                onClick={handleCopyFix}
                                className={cn(
                                    "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all",
                                    copied
                                        ? "bg-emerald-500/10 text-emerald-400"
                                        : "bg-primary/10 text-primary hover:bg-primary/20"
                                )}
                            >
                                {copied ? (
                                    <>
                                        <Check className="h-3 w-3" />
                                        Copied!
                                    </>
                                ) : (
                                    <>
                                        <Copy className="h-3 w-3" />
                                        Copy Fix
                                    </>
                                )}
                            </button>
                        </div>
                        <CodeViewer code={finding.suggestedFix} language="python" />
                    </div>
                </div>
            )}
        </div>
    );
}
