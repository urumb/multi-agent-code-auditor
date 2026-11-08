/**
 * API client for the Multi-Agent Code Auditor backend.
 *
 * All audit requests are sent to the FastAPI backend running at
 * NEXT_PUBLIC_API_URL (default: http://localhost:8000).
 */

import type { AuditInput, MetricData, TrendPoint, RecentAudit } from "@/types";

const DEFAULT_API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Resolves the backend API base URL, preferring a user override saved from
 * the Settings page (localStorage "apiUrl") over the build-time env default.
 * Read at call time (not module load) so a Settings change takes effect
 * immediately without a page reload.
 */
export function getApiBase(): string {
    if (typeof window === "undefined") return DEFAULT_API_BASE;
    try {
        const stored = window.localStorage.getItem("apiUrl");
        return stored && stored.trim().length > 0 ? stored.trim().replace(/\/+$/, "") : DEFAULT_API_BASE;
    } catch {
        return DEFAULT_API_BASE;
    }
}

/* ------------------------------------------------------------------ */
/*  Types matching the backend responses                                */
/* ------------------------------------------------------------------ */

export interface FileAuditResult {
    file_path: string;
    final_report: string;
    risk_score?: number;
    max_severity?: string;
    error: string | null;
}

export interface AuditResultResponse {
    total_files: number;
    results: FileAuditResult[];
}

export interface AuditHistoryEntry {
    id: string;
    repository: string;
    date: string;
    status: "pending" | "running" | "completed" | "failed";
    findings: number;
    max_severity: string;
    duration: number | null;
    input_type: string;
    /** Count of files whose individual audit errored/timed out — a job can
     * be "completed" (the run finished) while every file failed, which
     * reads very differently from a genuinely clean result. */
    files_errored: number;
}

export interface AuditHistoryDetail {
    id: string;
    repository: string;
    status: string;
    input_type: string;
    created_at: number;
    duration: number | null;
    error: string | null;
    total_files: number;
    results: FileAuditResult[];
}

export interface StreamLogEvent {
    agent: string;
    message: string;
    level: "info" | "warning" | "error" | "success";
}

export interface StreamFileEvent {
    path: string;
    index: number;
    total: number;
}

export interface ExecutionPlan {
    agents: string[];
    reason: string;
}

export interface AgentLifecycleEvent {
    agent: string;
}

export interface StreamCallbacks {
    onLog: (log: StreamLogEvent) => void;
    onResult: (result: FileAuditResult) => void;
    onFileStart: (data: StreamFileEvent) => void;
    onFileDone: (data: StreamFileEvent) => void;
    onExecutionPlan: (data: ExecutionPlan) => void;
    onAgentStarted: (data: AgentLifecycleEvent) => void;
    onAgentCompleted: (data: AgentLifecycleEvent) => void;
    onAgentFailed: (data: AgentLifecycleEvent) => void;
    onDone: (data: { total_files: number; duration?: number }) => void;
    onError: (error: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Core fetch helper                                                  */
/* ------------------------------------------------------------------ */

async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${getApiBase()}${endpoint}`, {
        ...options,
    });

    if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(`API error ${response.status}: ${text || response.statusText}`);
    }

    return response.json() as Promise<T>;
}

/* ------------------------------------------------------------------ */
/*  Background streaming audit (SSE via Job Queue)                     */
/* ------------------------------------------------------------------ */

/**
 * Starts a code audit in the background and returns a job_id.
 *
 * @param input - Audit input from the frontend form.
 * @returns Object containing the background job_id.
 */
/**
 * Pushes the model chosen on the Settings page to the backend. The backend
 * keeps it in memory only, so after a restart it would silently fall back to
 * the default while the UI still shows the saved choice. Best-effort: a
 * failure must never block starting an audit.
 */
async function syncSelectedModel(): Promise<void> {
    try {
        const model = window.localStorage.getItem("model");
        if (!model) return;
        await fetch(`${getApiBase()}/settings`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model }),
        });
    } catch {
        // ignore
    }
}

export async function fetchInstalledModels(): Promise<{ models: string[]; current: string }> {
    return apiFetch<{ models: string[]; current: string }>("/settings/models");
}

export async function startAuditJob(input: AuditInput): Promise<{ job_id: string }> {
    const body: Record<string, string> = {
        input_type: input.mode,
    };

    if (input.mode === "github" && input.githubUrl) {
        body.github_url = input.githubUrl;
    } else if (input.mode === "paste" && input.code) {
        body.code = input.code;
        if (input.language) body.language = input.language;
    }
    body.depth = input.depth ?? "full";

    await syncSelectedModel();
    return apiFetch<{ job_id: string }>("/audit/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

/**
 * Starts a file-upload audit in the background (with the same live SSE
 * progress as GitHub/paste) and returns a job_id.
 */
export async function startUploadJob(
    files: File[],
    depth: "quick" | "full" = "full",
): Promise<{ job_id: string }> {
    const formData = new FormData();
    formData.append("depth", depth);
    for (const file of files) {
        formData.append("files", file);
    }
    await syncSelectedModel();
    return apiFetch<{ job_id: string }>("/audit/stream/upload", {
        method: "POST",
        body: formData,
    });
}

/**
 * Subscribes to a background code audit via Server-Sent Events.
 *
 * Calls GET /audit/stream/{job_id} and reads the response body as a
 * ReadableStream, parsing structured JSON events and dispatching
 * to callbacks.
 *
 * @param jobId - UUID of the running audit job.
 * @param callbacks - Event handlers for each event type.
 */
export async function subscribeToAuditJob(
    jobId: string,
    callbacks: StreamCallbacks,
): Promise<void> {
    let response: Response;
    try {
        response = await fetch(`${getApiBase()}/audit/stream/${jobId}`, {
            method: "GET",
        });
    } catch {
        callbacks.onError("Failed to connect to backend stream");
        return;
    }

    if (!response.ok) {
        if (response.status === 404) {
            callbacks.onError("Job not found or expired");
        } else {
            callbacks.onError(`Backend error: ${response.status} ${response.statusText}`);
        }
        return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
        callbacks.onError("Stream not available");
        return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split("\n\n");
            buffer = lines.pop() ?? "";

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed.startsWith("data: ")) continue;

                const jsonStr = trimmed.slice(6);

                try {
                    const event = JSON.parse(jsonStr) as { type: string; data: unknown };

                    switch (event.type) {
                        case "log":
                            callbacks.onLog(event.data as StreamLogEvent);
                            break;
                        case "result":
                            callbacks.onResult(event.data as FileAuditResult);
                            break;
                        case "file_start":
                            callbacks.onFileStart(event.data as StreamFileEvent);
                            break;
                        case "file_done":
                            callbacks.onFileDone(event.data as StreamFileEvent);
                            break;
                        case "execution_plan":
                            callbacks.onExecutionPlan(event.data as ExecutionPlan);
                            break;
                        case "agent_started":
                            callbacks.onAgentStarted(event.data as AgentLifecycleEvent);
                            break;
                        case "agent_completed":
                            callbacks.onAgentCompleted(event.data as AgentLifecycleEvent);
                            break;
                        case "agent_failed":
                            callbacks.onAgentFailed(event.data as AgentLifecycleEvent);
                            break;
                        case "done":
                            callbacks.onDone(event.data as { total_files: number });
                            break;
                        case "error":
                            callbacks.onError((event.data as { message: string }).message);
                            break;
                    }
                } catch {
                    // Skip malformed JSON
                }
            }
        }
    } catch (err) {
        callbacks.onError(err instanceof Error ? err.message : "Stream interrupted");
    } finally {
        reader.releaseLock();
    }
}

/* ------------------------------------------------------------------ */
/*  Non-streaming fallback                                             */
/* ------------------------------------------------------------------ */

export async function submitAudit(input: AuditInput): Promise<AuditResultResponse> {
    if (input.mode === "upload" && input.files && input.files.length > 0) {
        const formData = new FormData();
        for (const file of input.files) {
            formData.append("files", file);
        }
        return apiFetch<AuditResultResponse>("/audit/upload", {
            method: "POST",
            body: formData,
        });
    }

    const body: Record<string, string> = {
        input_type: input.mode,
    };

    if (input.mode === "github" && input.githubUrl) {
        body.github_url = input.githubUrl;
    } else if (input.mode === "paste" && input.code) {
        body.code = input.code;
        if (input.language) body.language = input.language;
    }

    return apiFetch<AuditResultResponse>("/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

export async function fetchMetrics(): Promise<MetricData[]> {
    try {
        return await apiFetch<MetricData[]>("/metrics");
    } catch {
        return [];
    }
}

export async function fetchTrendData(): Promise<TrendPoint[]> {
    try {
        return await apiFetch<TrendPoint[]>("/trends");
    } catch {
        return [];
    }
}

export async function fetchRecentAudits(): Promise<RecentAudit[]> {
    try {
        return await apiFetch<RecentAudit[]>("/recent-audits");
    } catch {
        return [];
    }
}

export async function fetchAuditHistory(limit = 20, offset = 0): Promise<AuditHistoryEntry[]> {
    return apiFetch<AuditHistoryEntry[]>(`/audit/history?limit=${limit}&offset=${offset}`);
}

export async function fetchAuditHistoryDetail(jobId: string): Promise<AuditHistoryDetail> {
    return apiFetch<AuditHistoryDetail>(`/audit/history/${jobId}`);
}

export async function checkBackendHealth(): Promise<boolean> {
    try {
        const res = await fetch(`${getApiBase()}/health`, { method: "GET" });
        return res.ok;
    } catch {
        return false;
    }
}
