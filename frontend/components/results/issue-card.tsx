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
                "glass-card overflow-hidden animate-fade-in group transition-colors duration-200",
                finding.severity === "critical"
                    ? "border-destructive/30 hover:border-destructive/50"
                    : finding.severity === "warning"
                        ? "border-amber-500/30 hover:border-amber-500/50"
                        : "border-border hover:border-primary/30"
            )}
            style={{ animationDelay: `${index * 100}ms` }}
        >
            {/* Header */}
            <div className="p-4 bg-background">
                <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                            <SeverityBadge severity={finding.severity} />
                            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">
                                {finding.agent}
                            </span>
                        </div>
                        <h4 className="text-sm font-semibold text-foreground">
                            {finding.title}
                        </h4>
                        <div className="flex items-center gap-1.5 mt-2">
                            <FileCode className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground font-mono bg-secondary/50 px-1.5 py-0.5 rounded">
                                {finding.file}:{finding.line}
                            </span>
                            {finding.cwe && (
                                <span className="ml-2 inline-flex items-center rounded-md bg-secondary/50 px-2 py-0.5 text-[10px] font-medium text-muted-foreground border border-border">
                                    {finding.cwe}
                                </span>
                            )}
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={() => setExpanded(!expanded)}
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-secondary text-muted-foreground hover:text-foreground hover:bg-secondary/70 transition-colors"
                    >
                        {expanded ? (
                            <ChevronUp className="h-4 w-4" />
                        ) : (
                            <ChevronDown className="h-4 w-4" />
                        )}
                    </button>
                </div>

                <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                    {finding.description}
                </p>
            </div>

            {/* Expanded content */}
            {expanded && (
                <div className="border-t border-border px-4 py-5 space-y-5 bg-card">
                    {/* Original code */}
                    {finding.before_code && (
                      <div>
                          <p className="text-xs font-bold text-muted-foreground mb-2 uppercase tracking-wider">
                              Current Code
                          </p>
                          <CodeViewer
                              code={finding.before_code || finding.codeSnippet}
                              language="python"
                              highlightLine={1}
                          />
                      </div>
                    )}

                    {/* Suggested fix */}
                    {(finding.after_code || finding.suggestedFix) && (
                      <div>
                          <div className="flex items-center justify-between mb-2">
                              <p className="text-xs font-bold text-primary uppercase tracking-wider">
                                  Suggested Fix
                              </p>
                              <button
                                  type="button"
                                  onClick={handleCopyFix}
                                  className={cn(
                                      "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                                      copied
                                          ? "bg-primary text-primary-foreground"
                                          : "bg-primary/10 text-primary hover:bg-primary/20"
                                  )}
                              >
                                  {copied ? (
                                      <>
                                          <Check className="h-3 w-3" />
                                          Copied
                                      </>
                                  ) : (
                                      <>
                                          <Copy className="h-3 w-3" />
                                          Copy Fix
                                      </>
                                  )}
                              </button>
                          </div>
                          <CodeViewer code={finding.after_code || finding.suggestedFix} language="python" />
                      </div>
                    )}
                </div>
            )}
        </div>
    );
}
