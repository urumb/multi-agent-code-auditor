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
    { mode: "github", label: "GitHub Repository", icon: Github },
    { mode: "upload", label: "Upload Files", icon: Upload },
    { mode: "paste", label: "Paste Code", icon: Code },
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

    const handleSubmit = () => {
        onSubmit({ mode: inputMode, githubUrl, files, code, language });
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setFiles(Array.from(e.target.files));
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
        <div className="p-8 rounded-xl backdrop-blur-md bg-white/5 border border-white/10 shadow-xl hover:-translate-y-1 hover:shadow-2xl transition-all duration-200">
            {/* Mode tabs */}
            <div className="flex gap-2 mb-6">
                {tabs.map((tab) => (
                    <button
                        key={tab.mode}
                        type="button"
                        onClick={() => setInputMode(tab.mode)}
                        className={cn(
                            "flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200",
                            inputMode === tab.mode
                                ? "bg-primary/10 text-primary border border-primary/20"
                                : "bg-muted/30 text-muted-foreground hover:bg-muted/50 hover:text-foreground border border-transparent"
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
                    <label className="text-sm font-medium text-foreground" htmlFor="github-url">
                        Repository URL
                    </label>
                    <input
                        id="github-url"
                        type="url"
                        placeholder="https://github.com/user/repo"
                        value={githubUrl}
                        onChange={(e) => setGithubUrl(e.target.value)}
                        className="w-full rounded-lg border border-border bg-muted/30 px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 transition-all"
                    />
                </div>
            )}

            {/* File upload */}
            {inputMode === "upload" && (
                <div className="space-y-3">
                    <label className="text-sm font-medium text-foreground">
                        Upload Files
                    </label>
                    <div className="relative border-2 border-dashed border-border rounded-lg p-8 text-center hover:border-primary/40 transition-colors">
                        <FileUp className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
                        <p className="text-sm text-muted-foreground mb-2">
                            Drag and drop files here, or click to browse
                        </p>
                        <p className="text-xs text-muted-foreground/70">
                            ZIP archives or individual source files
                        </p>
                        <input
                            type="file"
                            multiple
                            onChange={handleFileChange}
                            className="absolute inset-0 opacity-0 cursor-pointer"
                            accept=".py,.js,.ts,.java,.zip,.jsx,.tsx"
                        />
                    </div>
                    {files.length > 0 && (
                        <div className="space-y-2 mt-3">
                            {files.map((file, index) => (
                                <div
                                    key={`${file.name}-${index}`}
                                    className="flex items-center justify-between rounded-lg bg-muted/20 px-3 py-2"
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
                        <label className="text-sm font-medium text-foreground" htmlFor="code-input">
                            Paste Code
                        </label>
                        <select
                            value={language}
                            onChange={(e) => setLanguage(e.target.value as ProgrammingLanguage)}
                            className="rounded-lg border border-border bg-muted/30 px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
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
                        className="w-full rounded-lg border border-border bg-muted/30 px-4 py-3 text-sm text-foreground font-mono placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 resize-none transition-all"
                    />
                </div>
            )}

            {/* Submit button */}
            <button
                type="button"
                onClick={handleSubmit}
                disabled={!isValid || isRunning}
                className={cn(
                    "mt-6 flex w-full items-center justify-center gap-2 rounded-lg px-6 py-3 text-sm font-semibold transition-all duration-200",
                    isValid && !isRunning
                        ? "bg-primary text-primary-foreground hover:opacity-90 glow-primary"
                        : "bg-muted text-muted-foreground cursor-not-allowed"
                )}
            >
                <Play className="h-4 w-4" />
                {isRunning ? "Audit Running..." : "Run Audit"}
            </button>
        </div>
    );
}
