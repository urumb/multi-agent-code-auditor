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
        <div className={cn("relative group rounded-xl overflow-hidden border border-white/5 bg-[#050505] shadow-inner", className)}>
            <div className="absolute top-0 left-0 w-full h-10 bg-[#101010] border-b border-white/5 flex items-center justify-between px-4 z-10">
                <div className="flex items-center gap-2">
                    <div className="flex gap-1.5 opacity-50 grayscale">
                        <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50"></div>
                        <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50"></div>
                        <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50"></div>
                    </div>
                    <span className="text-xs font-mono text-zinc-500 ml-2">{language}</span>
                </div>
                <button
                    type="button"
                    onClick={handleCopy}
                    className="flex h-7 w-7 items-center justify-center rounded bg-[#151515] border border-white/5 text-zinc-400 hover:text-foreground hover:bg-[#202020] transition-all opacity-0 group-hover:opacity-100"
                    title="Copy code"
                >
                    {copied ? (
                        <Check className="h-3.5 w-3.5 text-primary" />
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
                            backgroundColor: isHighlighted ? "rgba(34, 197, 94, 0.05)" : "transparent",
                            borderLeft: isHighlighted ? "3px solid #22c55e" : "3px solid transparent",
                            paddingLeft: "12px",
                            paddingRight: "16px",
                        };
                        return { style, className: isHighlighted ? "bg-primary/5" : "" };
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
