"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { AuditInputMode, ProgrammingLanguage } from "@/types";
import {
    Github,
    Upload,
    Code,
    Play,
    FileUp,
    X,
} from "lucide-react";

/**
 * Props for the AuditForm component.
 */
interface AuditFormProps {
    /** Callback fired when the user submits an audit request. */
    onSubmit: (data: {
        mode: AuditInputMode;
        githubUrl?: string;
        files?: File[];
        code?: string;
        language?: ProgrammingLanguage;
    }) => void;
    /** Whether an audit is currently running. */
    isRunning: boolean;
}

/** Tab configuration for input modes. */
const tabs: { mode: AuditInputMode; label: string; icon: React.ElementType }[] = [
    { mode: "github", label: "GitHub", icon: Github },
    { mode: "upload", label: "Upload", icon: Upload },
    { mode: "paste", label: "Paste", icon: Code },
];

/** Supported programming languages. */
const languages: { value: ProgrammingLanguage; label: string }[] = [
    { value: "python", label: "Python" },
    { value: "javascript", label: "JavaScript" },
    { value: "typescript", label: "TypeScript" },
    { value: "java", label: "Java" },
];

/**
 * Audit input form supporting three modes: GitHub URL, file upload, and code paste.
 *
 * @param props - Form configuration.
 */
export function AuditForm({ onSubmit, isRunning }: AuditFormProps) {
    const [inputMode, setInputMode] = useState<AuditInputMode>("github");
    const [githubUrl, setGithubUrl] = useState("");
    const [files, setFiles] = useState<File[]>([]);
    const [code, setCode] = useState("");
    const [language, setLanguage] = useState<ProgrammingLanguage>("python");
    const [dragging, setDragging] = useState(false);

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setDragging(false);
        const dropped = Array.from(e.dataTransfer.files);
        if (dropped.length) setFiles((prev) => [...prev, ...dropped]);
    };

    const handleSubmit = () => {
        onSubmit({ mode: inputMode, githubUrl, files, code, language });
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setFiles(Array.from(e.target.files));
            e.target.value = "";
        }
    };

    const removeFile = (index: number) => {
        setFiles((prev) => prev.filter((_, i) => i !== index));
    };

    const isValid =
        (inputMode === "github" && githubUrl.trim().length > 0) ||
        (inputMode === "upload" && files.length > 0) ||
        (inputMode === "paste" && code.trim().length > 0);

    return (
        <div className="glass-card p-6 sm:p-8">
            {/* Mode tabs */}
            <div className="mb-8 inline-flex gap-1 rounded-full border border-border bg-background/60 p-1">
                {tabs.map((tab) => (
                    <button
                        key={tab.mode}
                        type="button"
                        onClick={() => setInputMode(tab.mode)}
                        className={cn(
                            "flex items-center gap-2 rounded-full px-4 py-2 text-[0.8125rem] font-medium transition-all duration-300",
                            inputMode === tab.mode
                                ? "bg-secondary text-foreground shadow-sm shadow-black/40"
                                : "text-muted-foreground hover:text-foreground"
                        )}
                    >
                        <tab.icon className="h-4 w-4" />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* GitHub URL input */}
            {inputMode === "github" && (
                <div className="space-y-3">
                    <label className="eyebrow block" htmlFor="github-url">
                        Repository URL
                    </label>
                    <input
                        id="github-url"
                        type="url"
                        placeholder="https://github.com/user/repo"
                        value={githubUrl}
                        onChange={(e) => setGithubUrl(e.target.value)}
                        className="w-full rounded-xl border border-border bg-background/60 px-4 py-3.5 text-sm text-foreground placeholder:text-muted-foreground/60 transition-colors duration-300 focus:border-primary/50 focus:outline-none"
                    />
                </div>
            )}

            {/* File upload */}
            {inputMode === "upload" && (
                <div className="space-y-3">
                    <label className="eyebrow block">
                        Source files
                    </label>
                    <div
                        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                        onDragLeave={() => setDragging(false)}
                        onDrop={handleDrop}
                        className={cn(
                            "relative rounded-2xl border border-dashed p-10 text-center transition-all duration-300",
                            dragging ? "border-primary/70 bg-primary/5" : "border-border hover:border-[#3a3a42]"
                        )}
                    >
                        <FileUp className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
                        <p className="text-sm text-muted-foreground mb-2">
                            Drag and drop files here, or click to browse
                        </p>
                        <p className="text-xs text-muted-foreground/70">
                            ZIP archives or individual source files · up to 20MB
                        </p>
                        <input
                            type="file"
                            multiple
                            onChange={handleFileChange}
                            className="absolute inset-0 opacity-0 cursor-pointer"
                            accept=".py,.js,.jsx,.mjs,.ts,.tsx,.java,.c,.cpp,.h,.cs,.go,.rb,.php,.rs,.kt,.swift,.zip"
                        />
                    </div>
                    {files.length > 0 && (
                        <div className="space-y-2 mt-3">
                            {files.map((file, index) => (
                                <div
                                    key={`${file.name}-${index}`}
                                    className="flex items-center justify-between rounded-xl border border-border bg-background/40 px-3.5 py-2.5"
                                >
                                    <span className="text-sm text-foreground truncate">
                                        {file.name}
                                    </span>
                                    <button
                                        type="button"
                                        onClick={() => removeFile(index)}
                                        className="text-muted-foreground hover:text-red-400 transition-colors"
                                    >
                                        <X className="h-4 w-4" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Code paste */}
            {inputMode === "paste" && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <label className="eyebrow" htmlFor="code-input">
                            Source code
                        </label>
                        <select
                            value={language}
                            onChange={(e) => setLanguage(e.target.value as ProgrammingLanguage)}
                            className="rounded-full border border-border bg-background/60 px-3 py-1.5 text-xs text-foreground focus:border-primary/50 focus:outline-none"
                        >
                            {languages.map((lang) => (
                                <option key={lang.value} value={lang.value}>
                                    {lang.label}
                                </option>
                            ))}
                        </select>
                    </div>
                    <textarea
                        id="code-input"
                        placeholder="Paste your code here..."
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        rows={12}
                        className="w-full resize-none rounded-xl border border-border bg-background/60 px-4 py-3.5 font-mono text-[13px] leading-relaxed text-foreground placeholder:text-muted-foreground/60 transition-colors duration-300 focus:border-primary/50 focus:outline-none"
                    />
                </div>
            )}

            {/* Submit button */}
            <button
                type="button"
                onClick={handleSubmit}
                disabled={!isValid || isRunning}
                className={cn(
                    "mt-8 flex w-full items-center justify-center gap-2 rounded-full px-6 py-3.5 text-sm font-semibold transition-all duration-300",
                    isValid && !isRunning
                        ? "bg-foreground text-background hover:-translate-y-px hover:shadow-[0_10px_30px_-12px_rgba(59,239,140,0.5)] active:scale-[0.99]"
                        : "cursor-not-allowed bg-secondary text-muted-foreground"
                )}
            >
                <Play className="h-4 w-4" />
                {isRunning ? "Audit Running..." : "Run Audit"}
            </button>
        </div>
    );
}
