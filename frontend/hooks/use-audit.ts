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
    startUploadJob,
    subscribeToAuditJob,
    type AuditResultResponse,
    type FileAuditResult,
    type StreamLogEvent,
    type StreamFileEvent,
    type ExecutionPlan,
    type AgentLifecycleEvent,
} from "@/lib/api";

const MAX_LOGS = 100;
const JOB_STORAGE_KEY = "current_audit_job";

/** Maps an execution-plan agent key to its stage label. Order here defines
 * stage order — real order the pipeline runs in, not invented progress. */
const AGENT_STAGE_LABELS: [string, string][] = [
    ["security", "Security Analysis"],
    ["performance", "Performance Analysis"],
    ["quality", "Quality Analysis"],
    ["reviewer", "Reviewer Synthesis"],
];

/** Maps an SSE agent display name to its execution-plan key. */
const AGENT_NAME_TO_KEY: Record<string, string> = {
    "Security Agent": "security",
    "Performance Agent": "performance",
    "Quality Agent": "quality",
    "Reviewer Agent": "reviewer",
};

const AGENT_NODE_ID_MAP: Record<string, string> = {
    "Manager Agent": "manager",
    "Security Agent": "security",
    "Performance Agent": "performance",
    "Quality Agent": "code-quality",
    "Reviewer Agent": "reviewer",
};

export type AgentGraphNodeState = "idle" | "running" | "completed" | "failed";

const INITIAL_AGENT_GRAPH_STATES: Record<string, AgentGraphNodeState> = {
    manager: "idle",
    security: "idle",
    performance: "idle",
    "code-quality": "idle",
    reviewer: "idle",
};

/** Builds the initial (pre-execution-plan) stage list for an audit. GitHub
 * runs get an explicit "Cloning Repository" stage since that now happens as
 * a real, separately-reported background phase. */
function buildInitialStages(mode: AuditInput["mode"]): AuditStage[] {
    const labels = mode === "github" ? ["Cloning Repository", "Preparing Input"] : ["Preparing Input"];
    return labels.map((label, i) => ({
        id: i + 1,
        label,
        status: (i === 0 ? "running" : "pending") as AuditStage["status"],
    }));
}

/** Rebuilds the stage list once the real execution plan is known — one
 * stage per agent the backend actually decided to run, not a fixed list. */
function buildPlannedStages(agents: string[]): AuditStage[] {
    const labels = ["Preparing Input"];
    for (const [key, label] of AGENT_STAGE_LABELS) {
        if (agents.includes(key)) labels.push(label);
    }
    labels.push("Finalizing Report");
    return labels.map((label, i) => ({
        id: i + 1,
        label,
        status: (i === 0 ? "completed" : i === 1 ? "running" : "pending") as AuditStage["status"],
    }));
}

function isAutoRetryEnabled(): boolean {
    if (typeof window === "undefined") return false;
    try {
        return window.localStorage.getItem("autoRetry") !== "false";
    } catch {
        return false;
    }
}

interface UseAuditReturn {
    status: AuditStatus;
    stages: AuditStage[];
    logs: AgentLog[];
    result: AuditResultResponse | null;
    error: string | null;
    currentFile: string | null;
    currentAgent: string | null;
    duration: number | null;
    agentGraphStates: Record<string, AgentGraphNodeState>;
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
    const [stages, setStages] = useState<AuditStage[]>([]);
    const [logs, setLogs] = useState<AgentLog[]>([]);
    const [result, setResult] = useState<AuditResultResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [currentFile, setCurrentFile] = useState<string | null>(null);
    const [currentAgent, setCurrentAgent] = useState<string | null>(null);
    const [duration, setDuration] = useState<number | null>(null);
    const [agentGraphStates, setAgentGraphStates] =
        useState<Record<string, AgentGraphNodeState>>(INITIAL_AGENT_GRAPH_STATES);
    const resultsRef = useRef<FileAuditResult[]>([]);
    const lastInputRef = useRef<AuditInput | null>(null);
    const retriedRef = useRef(false);
    // Holds the latest runAudit implementation for the retry closure below,
    // which is defined (in _handleSubscription) before runAudit itself —
    // a ref sidesteps both the TDZ ordering issue and a circular useCallback
    // dependency between the two.
    const runAuditRef = useRef<(input: AuditInput) => Promise<void>>(async () => {});

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

    /** Marks every stage up to (and including) the one whose label matches
     * `label` as completed/running; leaves later stages untouched. */
    const activateStageByLabel = useCallback((label: string) => {
        setStages((prev) => {
            const idx = prev.findIndex((s) => s.label === label);
            if (idx === -1) return prev;
            return prev.map((s, i) => ({
                ...s,
                status: i < idx ? "completed" : i === idx ? "running" : s.status,
            }));
        });
    }, []);

    const completeStageByLabel = useCallback((label: string) => {
        setStages((prev) => prev.map((s) => (s.label === label ? { ...s, status: "completed" } : s)));
    }, []);

    const setAgentNodeState = useCallback((agent: string, nodeState: AgentGraphNodeState) => {
        const nodeId = AGENT_NODE_ID_MAP[agent];
        if (!nodeId) return;
        setAgentGraphStates((prev) => ({ ...prev, [nodeId]: nodeState }));
    }, []);

    // ------------------------------------------------------------------
    // Setup Subscription Handlers
    // ------------------------------------------------------------------
    const _handleSubscription = useCallback(
        async (jobId: string) => {
            setStatus("running");

            await subscribeToAuditJob(jobId, {
                onLog: (log: StreamLogEvent) => {
                    addLog(log.agent, log.message, log.level as AgentLog["level"]);
                    if (log.message.startsWith("Cloning repository")) {
                        activateStageByLabel("Cloning Repository");
                    } else if (log.message.startsWith("Cloned repository")) {
                        completeStageByLabel("Cloning Repository");
                        activateStageByLabel("Preparing Input");
                    }
                },
                onFileStart: (data: StreamFileEvent) => {
                    setCurrentFile(data.path);
                    completeStageByLabel("Cloning Repository");
                    activateStageByLabel("Preparing Input");
                },
                onFileDone: () => {},
                onExecutionPlan: (plan: ExecutionPlan) => {
                    addLog("Manager Agent", `Execution plan: ${plan.reason} (${plan.agents.join(", ")})`, "info");
                    setStages(buildPlannedStages(plan.agents));
                },
                onAgentStarted: (data: AgentLifecycleEvent) => {
                    setAgentNodeState(data.agent, "running");
                    const key = AGENT_NAME_TO_KEY[data.agent];
                    const label = AGENT_STAGE_LABELS.find(([k]) => k === key)?.[1];
                    if (label) activateStageByLabel(label);
                },
                onAgentCompleted: (data: AgentLifecycleEvent) => {
                    setAgentNodeState(data.agent, "completed");
                    const key = AGENT_NAME_TO_KEY[data.agent];
                    const label = AGENT_STAGE_LABELS.find(([k]) => k === key)?.[1];
                    if (label) {
                        completeStageByLabel(label);
                        activateStageByLabel("Finalizing Report");
                    }
                },
                onAgentFailed: (data: AgentLifecycleEvent) => {
                    setAgentNodeState(data.agent, "failed");
                },
                onResult: (fileResult: FileAuditResult) => {
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
                onDone: (data: { total_files: number; files_skipped?: number; duration?: number }) => {
                    const finalResult: AuditResultResponse = {
                        total_files: data.total_files,
                        files_skipped: data.files_skipped ?? 0,
                        results: resultsRef.current,
                    };

                    setStages((prev) => prev.map((s) => ({ ...s, status: "completed" as const })));
                    setResult(finalResult);
                    setStatus("completed");
                    setCurrentFile(null);
                    setCurrentAgent(null);
                    setDuration(data.duration ?? null);

                    localStorage.setItem("latestAuditResult", JSON.stringify(finalResult));
                    localStorage.removeItem(JOB_STORAGE_KEY);

                    addLog("System", `✓ Audit complete — ${data.total_files} file(s) processed in ${data.duration ? data.duration + 's' : 'unknown time'}`, "success");
                },
                onError: (errorMsg: string) => {
                    if (errorMsg.includes("Job not found")) {
                        localStorage.removeItem(JOB_STORAGE_KEY);
                        setStatus("idle");
                        return;
                    }

                    localStorage.removeItem(JOB_STORAGE_KEY);

                    if (!retriedRef.current && isAutoRetryEnabled() && lastInputRef.current) {
                        retriedRef.current = true;
                        addLog("System", `✗ ${errorMsg}`, "error");
                        addLog("System", "Auto-retry is on — retrying this audit once...", "warning");
                        const retryInput = lastInputRef.current;
                        window.setTimeout(() => {
                            void runAuditRef.current(retryInput);
                        }, 1000);
                        return;
                    }

                    setError(errorMsg);
                    setStatus("failed");
                    setCurrentFile(null);
                    setCurrentAgent(null);
                    addLog("System", `✗ ${errorMsg}`, "error");

                    setStages((prev) =>
                        prev.map((s) => (s.status === "running" ? { ...s, status: "error" as const } : s))
                    );
                },
            });
        },
        [addLog, activateStageByLabel, completeStageByLabel, setAgentNodeState]
    );

    // ------------------------------------------------------------------
    // Background Job Persistence Lifecycle
    // ------------------------------------------------------------------
    useEffect(() => {
        const storedJobId = localStorage.getItem(JOB_STORAGE_KEY);
        if (storedJobId && status === "idle") {
            window.setTimeout(() => {
                addLog("System", "Reconnecting to active background audit...", "info");
                _handleSubscription(storedJobId).catch((err) => {
                    const message = err instanceof Error ? err.message : "Failed to reconnect";
                    addLog("System", `✗ ${message}`, "error");
                    localStorage.removeItem(JOB_STORAGE_KEY);
                    setStatus("idle");
                });
            }, 0);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const runAudit = useCallback(
        async (input: AuditInput) => {
            setStatus("running");
            setError(null);
            setLogs([]);
            setResult(null);
            setCurrentFile(null);
            setCurrentAgent(null);
            setAgentGraphStates(INITIAL_AGENT_GRAPH_STATES);
            resultsRef.current = [];
            setStages(buildInitialStages(input.mode));

            addLog("System", `Audit started — input type: ${input.mode}`, "info");

            try {
                const { job_id } =
                    input.mode === "upload"
                        ? await startUploadJob(input.files ?? [], input.depth ?? "full")
                        : await startAuditJob(input);
                localStorage.setItem(JOB_STORAGE_KEY, job_id);
                await _handleSubscription(job_id);
            } catch (err) {
                const message = err instanceof Error ? err.message : "Failed to start job";
                setError(message);
                setStatus("failed");
                addLog("System", `✗ ${message}`, "error");
            }
        },
        [addLog, _handleSubscription]
    );
    runAuditRef.current = runAudit;

    const startAudit = useCallback(
        async (input: AuditInput) => {
            lastInputRef.current = input;
            retriedRef.current = false;
            await runAudit(input);
        },
        [runAudit]
    );

    const reset = useCallback(() => {
        setStatus("idle");
        setStages([]);
        setLogs([]);
        setResult(null);
        setError(null);
        setCurrentFile(null);
        setCurrentAgent(null);
        setAgentGraphStates(INITIAL_AGENT_GRAPH_STATES);
        resultsRef.current = [];
        lastInputRef.current = null;
        localStorage.removeItem(JOB_STORAGE_KEY);
    }, []);

    return {
        status,
        stages,
        logs,
        result,
        error,
        currentFile,
        currentAgent,
        duration,
        agentGraphStates,
        startAudit,
        reset,
    };
}
