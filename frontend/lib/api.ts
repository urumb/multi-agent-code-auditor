/**
 * API client for the Multi-Agent Code Auditor backend.
 *
 * All audit requests are sent to the FastAPI backend running at
 * NEXT_PUBLIC_API_URL (default: http://localhost:8000).
 */

import type { AuditInput, MetricData, TrendPoint, RecentAudit } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  Types matching the backend responses                                */
/* ------------------------------------------------------------------ */

/** A single file's audit result from the backend. */
export interface FileAuditResult {
    file_path: string;
    final_report: string;
    error: string | null;
}

/** Aggregated audit response from the backend. */
export interface AuditResultResponse {
    total_files: number;
    results: FileAuditResult[];
}

/** A real-time log event from the SSE stream. */
export interface StreamLogEvent {
    agent: string;
    message: string;
    level: "info" | "warning" | "error" | "success";
}

/** File progress event from the SSE stream. */
export interface StreamFileEvent {
    path: string;
    index: number;
    total: number;
}

/** Callbacks for the SSE stream consumer. */
export interface StreamCallbacks {
    onLog: (log: StreamLogEvent) => void;
    onResult: (result: FileAuditResult) => void;
    onFileStart: (data: StreamFileEvent) => void;
    onFileDone: (data: StreamFileEvent) => void;
    onDone: (data: { total_files: number }) => void;
    onError: (error: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Core fetch helper                                                  */
/* ------------------------------------------------------------------ */

/**
 * Performs a fetch request against the backend API.
 *
 * @param endpoint - API endpoint path (e.g. "/audit").
 * @param options  - Optional fetch init configuration.
 * @returns The parsed JSON response.
 * @throws Error on non-2xx responses.
 */
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
    });

    if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(`API error ${response.status}: ${text || response.statusText}`);
    }

    return response.json() as Promise<T>;
}

/* ------------------------------------------------------------------ */
/*  Streaming audit (SSE via POST)                                     */
/* ------------------------------------------------------------------ */

/**
 * Streams a code audit via Server-Sent Events.
 *
 * Sends a POST to /audit/stream and reads the response body as a
 * ReadableStream, parsing structured JSON events and dispatching
 * to callbacks.
 *
 * Event format: ``data: {"type":"log|result|file_start|file_done|done|error","data":{...}}``
 *
 * @param input - Audit input from the frontend form.
 * @param callbacks - Event handlers for each event type.
 */
export async function streamAudit(
    input: AuditInput,
    callbacks: StreamCallbacks,
): Promise<void> {
    const body: Record<string, string> = {
        input_type: input.mode,
    };

    if (input.mode === "github" && input.githubUrl) {
        body.github_url = input.githubUrl;
    } else if (input.mode === "paste" && input.code) {
        body.code = input.code;
    }

    let response: Response;
    try {
        response = await fetch(`${API_BASE}/audit/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
    } catch {
        callbacks.onError("Failed to connect to backend");
        return;
    }

    if (!response.ok) {
        callbacks.onError(`Backend error: ${response.status} ${response.statusText}`);
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

            // Process complete SSE lines (each ends with \n\n)
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

/**
 * Submits a code audit request (non-streaming fallback).
 *
 * @param input - Audit input from the frontend form.
 * @returns The backend's AuditResultResponse.
 */
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
    }

    return apiFetch<AuditResultResponse>("/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

/* ------------------------------------------------------------------ */
/*  Dashboard endpoints (no backend support yet — return empty)        */
/* ------------------------------------------------------------------ */

export async function fetchMetrics(): Promise<MetricData[]> {
    return [];
}

export async function fetchTrendData(): Promise<TrendPoint[]> {
    return [];
}

export async function fetchRecentAudits(): Promise<RecentAudit[]> {
    return [];
}
