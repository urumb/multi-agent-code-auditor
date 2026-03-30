"use client";

import { useState, useCallback, useRef } from "react";
import type {
    AuditInput,
    AuditStatus,
    AgentLog,
    AuditStage,
} from "@/types";
import {
    streamAudit,
    submitAudit,
    type AuditResultResponse,
    type FileAuditResult,
    type StreamLogEvent,
    type StreamFileEvent,
} from "@/lib/api";

/** Maximum number of log entries to keep in state (backpressure). */
const MAX_LOGS = 100;

/** Audit stages shown in the progress indicator. */
const AUDIT_STAGES: AuditStage[] = [
    { id: 1, label: "Processing Input", status: "pending" },
    { id: 2, label: "Security Analysis", status: "pending" },
    { id: 3, label: "Performance Analysis", status: "pending" },
    { id: 4, label: "Reviewer Synthesis", status: "pending" },
    { id: 5, label: "Finalizing Report", status: "pending" },
];

/** Maps agent names from backend to stage IDs. */
const AGENT_STAGE_MAP: Record<string, number> = {
    "Manager Agent": 1,
    "Security Agent": 2,
    "Performance Agent": 3,
    "Reviewer Agent": 4,
};

/** Return type for the useAudit hook. */
interface UseAuditReturn {
    status: AuditStatus;
    stages: AuditStage[];
    logs: AgentLog[];
    result: AuditResultResponse | null;
    error: string | null;
    currentFile: string | null;
    currentAgent: string | null;
    startAudit: (input: AuditInput) => Promise<void>;
    reset: () => void;
}

/** Generates a unique ID for log entries. */
let logCounter = 0;
function nextLogId(): string {
    logCounter += 1;
    return `log-${logCounter}`;
}

/** Returns a formatted timestamp string. */
function timestamp(): string {
    return new Date().toLocaleTimeString("en-GB", { hour12: false });
}

/**
 * Custom hook for managing audit lifecycle with real-time SSE streaming.
 *
 * Uses the streaming endpoint for github/paste inputs and falls back
 * to the non-streaming endpoint for file uploads.
 *
 * @returns Audit state and control functions.
 */
export function useAudit(): UseAuditReturn {
    const [status, setStatus] = useState<AuditStatus>("idle");
    const [stages, setStages] = useState<AuditStage[]>(AUDIT_STAGES);
    const [logs, setLogs] = useState<AgentLog[]>([]);
    const [result, setResult] = useState<AuditResultResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [currentFile, setCurrentFile] = useState<string | null>(null);
    const [currentAgent, setCurrentAgent] = useState<string | null>(null);
    const resultsRef = useRef<FileAuditResult[]>([]);

    /** Adds a log entry with backpressure protection. */
    const addLog = useCallback(
        (agent: string, message: string, level: AgentLog["level"] = "info") => {
            setLogs((prev) => [
                ...prev.slice(-MAX_LOGS + 1),
                { id: nextLogId(), timestamp: timestamp(), agent, message, level },
            ]);
            setCurrentAgent(agent);
        },
        []
    );

    /** Updates a single stage status. */
    const updateStage = useCallback(
        (id: number, stageStatus: AuditStage["status"]) => {
            setStages((prev) =>
                prev.map((s) => (s.id === id ? { ...s, status: stageStatus } : s))
            );
        },
        []
    );

    /** Marks a stage as running and all previous stages as completed. */
    const activateStage = useCallback(
        (stageId: number) => {
            setStages((prev) =>
                prev.map((s) => ({
                    ...s,
                    status:
                        s.id < stageId
                            ? "completed"
                            : s.id === stageId
                              ? "running"
                              : s.status,
                }))
            );
        },
        []
    );

    /** Starts a streaming audit (github / paste). */
    const startStreamingAudit = useCallback(
        async (input: AuditInput) => {
            setStatus("running");
            setError(null);
            setLogs([]);
            setResult(null);
            setCurrentFile(null);
            setCurrentAgent(null);
            resultsRef.current = [];
            setStages(AUDIT_STAGES.map((s) => ({ ...s, status: "pending" as const })));

            updateStage(1, "running");
            addLog("System", `Audit started — input type: ${input.mode}`, "info");

            await streamAudit(input, {
                onLog: (log: StreamLogEvent) => {
                    addLog(log.agent, log.message, log.level as AgentLog["level"]);

                    // Update stages based on agent name
                    const stageId = AGENT_STAGE_MAP[log.agent];
                    if (stageId) {
                        activateStage(stageId);
                    }
                },

                onFileStart: (data: StreamFileEvent) => {
                    setCurrentFile(data.path);
                    updateStage(1, "completed");
                    updateStage(2, "running");
                },

                onFileDone: (_data: StreamFileEvent) => {
                    // File done — stage updates handled by onDone
                },

                onResult: (fileResult: FileAuditResult) => {
                    resultsRef.current = [...resultsRef.current, fileResult];
                    const statusIcon = fileResult.error ? "✗" : "✓";
                    addLog(
                        "System",
                        `${statusIcon} ${fileResult.file_path}`,
                        fileResult.error ? "warning" : "success"
                    );
                },

                onDone: (data: { total_files: number }) => {
                    const finalResult: AuditResultResponse = {
                        total_files: data.total_files,
                        results: resultsRef.current,
                    };

                    setStages((prev) =>
                        prev.map((s) => ({ ...s, status: "completed" as const }))
                    );

                    setResult(finalResult);
                    setStatus("completed");
                    setCurrentFile(null);
                    setCurrentAgent(null);

                    localStorage.setItem(
                        "latestAuditResult",
                        JSON.stringify(finalResult)
                    );

                    addLog(
                        "System",
                        `✓ Audit complete — ${data.total_files} file(s) processed`,
                        "success"
                    );
                },

                onError: (errorMsg: string) => {
                    setError(errorMsg);
                    setStatus("failed");
                    setCurrentFile(null);
                    setCurrentAgent(null);
                    addLog("System", `✗ ${errorMsg}`, "error");

                    setStages((prev) =>
                        prev.map((s) =>
                            s.status === "running"
                                ? { ...s, status: "error" as const }
                                : s
                        )
                    );
                },
            });
        },
        [addLog, updateStage, activateStage]
    );

    /** Starts a non-streaming audit (file upload fallback). */
    const startUploadAudit = useCallback(
        async (input: AuditInput) => {
            setStatus("running");
            setError(null);
            setLogs([]);
            setResult(null);
            setCurrentFile(null);
            setCurrentAgent(null);
            setStages(AUDIT_STAGES.map((s) => ({ ...s, status: "pending" as const })));

            updateStage(1, "running");
            addLog("System", `Upload audit started — ${input.files?.length ?? 0} file(s)`, "info");

            try {
                updateStage(1, "completed");
                updateStage(2, "running");
                addLog("System", "Uploading files to backend...", "info");

                const auditResult = await submitAudit(input);

                setStages((prev) =>
                    prev.map((s) => ({ ...s, status: "completed" as const }))
                );
                setResult(auditResult);
                setStatus("completed");

                localStorage.setItem(
                    "latestAuditResult",
                    JSON.stringify(auditResult)
                );

                addLog(
                    "System",
                    `✓ Audit complete — ${auditResult.total_files} file(s) processed`,
                    "success"
                );
            } catch (err) {
                const message = err instanceof Error ? err.message : "Audit failed";
                setError(message);
                setStatus("failed");
                addLog("System", `✗ ${message}`, "error");

                setStages((prev) =>
                    prev.map((s) =>
                        s.status === "running"
                            ? { ...s, status: "error" as const }
                            : s
                    )
                );
            }
        },
        [addLog, updateStage]
    );

    /** Starts an audit — streaming for github/paste, fallback for upload. */
    const startAudit = useCallback(
        async (input: AuditInput) => {
            if (input.mode === "upload") {
                await startUploadAudit(input);
            } else {
                await startStreamingAudit(input);
            }
        },
        [startStreamingAudit, startUploadAudit]
    );

    /** Resets all audit state to initial values. */
    const reset = useCallback(() => {
        setStatus("idle");
        setStages(AUDIT_STAGES);
        setLogs([]);
        setResult(null);
        setError(null);
        setCurrentFile(null);
        setCurrentAgent(null);
        resultsRef.current = [];
    }, []);

    return { status, stages, logs, result, error, currentFile, currentAgent, startAudit, reset };
}
