"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import type {
    AuditInput,
    AuditStatus,
    AgentLog,
    AuditStage,
} from "@/types";
import {
    startAuditJob,
    subscribeToAuditJob,
    submitAudit,
    type AuditResultResponse,
    type FileAuditResult,
    type StreamLogEvent,
    type StreamFileEvent,
} from "@/lib/api";

const MAX_LOGS = 100;
const JOB_STORAGE_KEY = "current_audit_job";

const AUDIT_STAGES: AuditStage[] = [
    { id: 1, label: "Processing Input", status: "pending" },
    { id: 2, label: "Security Analysis", status: "pending" },
    { id: 3, label: "Performance Analysis", status: "pending" },
    { id: 4, label: "Reviewer Synthesis", status: "pending" },
    { id: 5, label: "Finalizing Report", status: "pending" },
];

const AGENT_STAGE_MAP: Record<string, number> = {
    "Manager Agent": 1,
    "Security Agent": 2,
    "Performance Agent": 3,
    "Reviewer Agent": 4,
};

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

let logCounter = 0;
function nextLogId(): string {
    logCounter += 1;
    return `log-${logCounter}`;
}

function timestamp(): string {
    return new Date().toLocaleTimeString("en-GB", { hour12: false });
}

export function useAudit(): UseAuditReturn {
    const [status, setStatus] = useState<AuditStatus>("idle");
    const [stages, setStages] = useState<AuditStage[]>(AUDIT_STAGES);
    const [logs, setLogs] = useState<AgentLog[]>([]);
    const [result, setResult] = useState<AuditResultResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [currentFile, setCurrentFile] = useState<string | null>(null);
    const [currentAgent, setCurrentAgent] = useState<string | null>(null);
    const resultsRef = useRef<FileAuditResult[]>([]);

    // ------------------------------------------------------------------
    // State updaters
    // ------------------------------------------------------------------
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

    const updateStage = useCallback(
        (id: number, stageStatus: AuditStage["status"]) => {
            setStages((prev) =>
                prev.map((s) => (s.id === id ? { ...s, status: stageStatus } : s))
            );
        },
        []
    );

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

    // ------------------------------------------------------------------
    // Setup Subscription Handlers
    // ------------------------------------------------------------------
    const _handleSubscription = useCallback(
        async (jobId: string) => {
            setStatus("running");

            await subscribeToAuditJob(jobId, {
                onLog: (log: StreamLogEvent) => {
                    addLog(log.agent, log.message, log.level as AgentLog["level"]);
                    const stageId = AGENT_STAGE_MAP[log.agent];
                    if (stageId) activateStage(stageId);
                },
                onFileStart: (data: StreamFileEvent) => {
                    setCurrentFile(data.path);
                    updateStage(1, "completed");
                    updateStage(2, "running");
                },
                onFileDone: () => {},
                onResult: (fileResult: FileAuditResult) => {
                    // Update results array without duplicates (in case of reconnects)
                    if (!resultsRef.current.find(r => r.file_path === fileResult.file_path)) {
                        resultsRef.current = [...resultsRef.current, fileResult];
                        const statusIcon = fileResult.error ? "✗" : "✓";
                        addLog(
                            "System",
                            `${statusIcon} ${fileResult.file_path}`,
                            fileResult.error ? "warning" : "success"
                        );
                    }
                },
                onDone: (data: { total_files: number }) => {
                    const finalResult: AuditResultResponse = {
                        total_files: data.total_files,
                        results: resultsRef.current,
                    };

                    setStages((prev) => prev.map((s) => ({ ...s, status: "completed" as const })));
                    setResult(finalResult);
                    setStatus("completed");
                    setCurrentFile(null);
                    setCurrentAgent(null);

                    localStorage.setItem("latestAuditResult", JSON.stringify(finalResult));
                    localStorage.removeItem(JOB_STORAGE_KEY);

                    addLog("System", `✓ Audit complete — ${data.total_files} file(s) processed`, "success");
                },
                onError: (errorMsg: string) => {
                    // Ignore "Job not found" if we reloaded the page long after it finished
                    if (errorMsg.includes("Job not found")) {
                        localStorage.removeItem(JOB_STORAGE_KEY);
                        setStatus("idle");
                        return;
                    }

                    setError(errorMsg);
                    setStatus("failed");
                    setCurrentFile(null);
                    setCurrentAgent(null);
                    localStorage.removeItem(JOB_STORAGE_KEY);
                    addLog("System", `✗ ${errorMsg}`, "error");

                    setStages((prev) =>
                        prev.map((s) => (s.status === "running" ? { ...s, status: "error" as const } : s))
                    );
                },
            });
        },
        [addLog, updateStage, activateStage]
    );

    // ------------------------------------------------------------------
    // Background Job Persistence Lifecycle
    // ------------------------------------------------------------------
    // Mount: Check if a job is already running
    useEffect(() => {
        const storedJobId = localStorage.getItem(JOB_STORAGE_KEY);
        if (storedJobId && status === "idle") {
            addLog("System", "Reconnecting to active background audit...", "info");
            _handleSubscription(storedJobId);
        }
    }, [status, _handleSubscription, addLog]);

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

            try {
                const { job_id } = await startAuditJob(input);
                localStorage.setItem(JOB_STORAGE_KEY, job_id);
                await _handleSubscription(job_id);
            } catch (err) {
                const message = err instanceof Error ? err.message : "Failed to start job";
                setError(message);
                setStatus("failed");
                addLog("System", `✗ ${message}`, "error");
            }
        },
        [addLog, updateStage, _handleSubscription]
    );

    // ------------------------------------------------------------------
    // Local / Fallback modes
    // ------------------------------------------------------------------
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

                setStages((prev) => prev.map((s) => ({ ...s, status: "completed" as const })));
                setResult(auditResult);
                setStatus("completed");

                localStorage.setItem("latestAuditResult", JSON.stringify(auditResult));
                addLog("System", `✓ Audit complete — ${auditResult.total_files} file(s) processed`, "success");
            } catch (err) {
                const message = err instanceof Error ? err.message : "Audit failed";
                setError(message);
                setStatus("failed");
                addLog("System", `✗ ${message}`, "error");
            }
        },
        [addLog, updateStage]
    );

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

    const reset = useCallback(() => {
        setStatus("idle");
        setStages(AUDIT_STAGES);
        setLogs([]);
        setResult(null);
        setError(null);
        setCurrentFile(null);
        setCurrentAgent(null);
        resultsRef.current = [];
        localStorage.removeItem(JOB_STORAGE_KEY);
    }, []);

    return { status, stages, logs, result, error, currentFile, currentAgent, startAudit, reset };
}
