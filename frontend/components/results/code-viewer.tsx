"use client";

import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { cn } from "@/lib/utils";
import { Copy, Check } from "lucide-react";

/**
 * Props for the CodeViewer component.
 */
interface CodeViewerProps {
    /** Code string to display. */
    code: string;
    /** Programming language for syntax highlighting. */
    language?: string;
    /** Specific line number to highlight as affected. */
    highlightLine?: number;
    /** Additional CSS classes. */
    className?: string;
}

/**
 * Syntax-highlighted code viewer with line numbers, affected-line highlighting,
 * and a copy-to-clipboard button.
 *
 * @param props - Code viewer configuration.
 */
export function CodeViewer({
    code,
    language = "python",
    highlightLine,
    className,
}: CodeViewerProps) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // Clipboard API not available
        }
    };

    return (
        <div className={cn("relative group rounded-xl overflow-hidden border border-slate-800 bg-[#0f172a] shadow-inner", className)}>
            <div className="absolute top-0 left-0 w-full h-10 bg-slate-900/50 border-b border-slate-800 flex items-center justify-between px-4 z-10">
                <div className="flex items-center gap-2">
                    <div className="flex gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50"></div>
                        <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50"></div>
                        <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50"></div>
                    </div>
                    <span className="text-xs font-mono text-slate-500 ml-2">{language}</span>
                </div>
                <button
                    type="button"
                    onClick={handleCopy}
                    className="flex h-7 w-7 items-center justify-center rounded bg-slate-800 border border-slate-700 text-slate-400 hover:text-foreground hover:bg-slate-700 transition-all opacity-0 group-hover:opacity-100"
                    title="Copy code"
                >
                    {copied ? (
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                        <Copy className="h-3.5 w-3.5" />
                    )}
                </button>
            </div>

            <div className="pt-10">
                <SyntaxHighlighter
                    language={language}
                    style={vscDarkPlus}
                    showLineNumbers
                    wrapLines
                    lineProps={(lineNumber: number) => {
                        const isHighlighted = highlightLine && lineNumber === highlightLine;
                        const style: React.CSSProperties = {
                            display: "block",
                            backgroundColor: isHighlighted ? "rgba(239, 68, 68, 0.15)" : "transparent",
                            borderLeft: isHighlighted ? "3px solid #ef4444" : "3px solid transparent",
                            paddingLeft: "12px",
                            paddingRight: "16px",
                        };
                        return { style, className: isHighlighted ? "bg-red-500/10" : "" };
                    }}
                    customStyle={{
                        margin: 0,
                        padding: "1rem 0",
                        fontSize: "13px",
                        background: "transparent",
                    }}
                >
                    {code}
                </SyntaxHighlighter>
            </div>
        </div>
    );
}
