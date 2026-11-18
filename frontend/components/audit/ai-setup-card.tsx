"use client";

import { useCallback, useEffect, useState } from "react";
import { Brain, Download, ExternalLink, RefreshCw, Wrench } from "lucide-react";
import { toast } from "sonner";
import { fetchAiStatus, setAiEnabled, startModelPull, type AiStatus } from "@/lib/api";

const OLLAMA_DOWNLOAD_URL = "https://ollama.com/download";

/**
 * Shown above the audit form when AI is on but not ready: Ollama isn't
 * running, or the chosen model isn't downloaded yet. Offers the fix (install
 * link / one-click model download with progress) or tools-only mode instead.
 * Renders nothing when everything is ready or AI is off.
 */
export function AiSetupCard() {
    const [status, setStatus] = useState<AiStatus | null>(null);
    const [checking, setChecking] = useState(false);

    const refresh = useCallback(() => {
        return fetchAiStatus()
            .then(setStatus)
            .catch(() => setStatus(null)); // backend down: the header already says so
    }, []);

    useEffect(() => {
        void refresh();
    }, [refresh]);

    // While a download runs, poll its progress.
    const pulling = status?.pull.status === "pulling";
    useEffect(() => {
        if (!pulling) return;
        const timer = setInterval(() => void refresh(), 1000);
        return () => clearInterval(timer);
    }, [pulling, refresh]);

    if (!status || !status.ai_enabled) return null;
    if (status.ollama_reachable && status.model_installed && !pulling) return null;

    const checkAgain = async () => {
        setChecking(true);
        await refresh();
        setChecking(false);
    };

    const useToolsOnly = async () => {
        try {
            await setAiEnabled(false);
            toast.success("Tools-only mode: audits use bandit, ruff and semgrep. Turn AI back on in Settings.");
            await refresh();
        } catch {
            toast.error("Couldn't change the setting.");
        }
    };

    const download = async () => {
        try {
            await startModelPull(status.model);
            await refresh();
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "Couldn't start the download.");
        }
    };

    const pull = status.pull;
    const percent = pull.total > 0 ? Math.min(100, Math.round((pull.completed / pull.total) * 100)) : 0;

    return (
        <div role="region" aria-label="AI setup" className="glass-card space-y-4 border-amber-500/20 p-5">
            <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-foreground">
                    {!status.ollama_reachable ? "AI agents need Ollama" : "Download the AI model"}
                </h3>
            </div>

            {!status.ollama_reachable ? (
                <p className="text-sm text-muted-foreground">
                    Ollama runs the AI models on this computer, for free. It isn&apos;t running right now.
                    Install it (or start it if it&apos;s installed), then check again. Until then you can
                    run tools-only audits.
                </p>
            ) : pulling ? (
                <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                        Downloading <span className="font-mono text-foreground">{pull.model}</span>... {percent}%
                    </p>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-muted" aria-hidden>
                        <div className="h-full bg-primary transition-all" style={{ width: `${percent}%` }} />
                    </div>
                </div>
            ) : (
                <p className="text-sm text-muted-foreground">
                    The model <span className="font-mono text-foreground">{status.model}</span> isn&apos;t
                    downloaded yet (about 2 GB, free).
                    {pull.status === "error" && pull.error && (
                        <span className="mt-1 block text-red-400">Last download failed: {pull.error}</span>
                    )}
                </p>
            )}

            {!pulling && (
                <div className="flex flex-wrap gap-2">
                    {!status.ollama_reachable ? (
                        <>
                            <a
                                href={OLLAMA_DOWNLOAD_URL}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90"
                            >
                                <ExternalLink className="h-4 w-4" />
                                Get Ollama
                            </a>
                            <button
                                type="button"
                                onClick={checkAgain}
                                disabled={checking}
                                className="flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm font-medium text-foreground hover:bg-muted disabled:opacity-50"
                            >
                                <RefreshCw className={`h-4 w-4 ${checking ? "animate-spin" : ""}`} />
                                Check again
                            </button>
                        </>
                    ) : (
                        <button
                            type="button"
                            onClick={download}
                            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90"
                        >
                            <Download className="h-4 w-4" />
                            Download {status.model}
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={useToolsOnly}
                        className="flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
                    >
                        <Wrench className="h-4 w-4" />
                        Use tools-only
                    </button>
                </div>
            )}
        </div>
    );
}
