"use client";

import { useState, useCallback, useRef } from "react";
import type {
    AuditInput,
    AuditResult,
    AuditStatus,
    AgentLog,
    AuditStage,
} from "@/types";
import { submitAudit } from "@/lib/api";
import { mockAgentLogs, defaultAuditStages } from "@/lib/mock-data";

/** Return type for the useAudit hook. */
interface UseAuditReturn {
    status: AuditStatus;
    stages: AuditStage[];
    logs: AgentLog[];
    result: AuditResult | null;
    error: string | null;
    startAudit: (input: AuditInput) => Promise<void>;
    reset: () => void;
}

/**
 * Custom hook for managing audit lifecycle: submission, progress tracking,
 * agent log streaming, and result storage.
 *
 * @returns Audit state and control functions.
 */
export function useAudit(): UseAuditReturn {
    const [status, setStatus] = useState<AuditStatus>("idle");
    const [stages, setStages] = useState<AuditStage[]>(defaultAuditStages);
    const [logs, setLogs] = useState<AgentLog[]>([]);
    const [result, setResult] = useState<AuditResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const intervalRef = useRef<NodeJS.Timeout | null>(null);

    /** Simulates streaming agent logs during mock mode. */
    const simulateLogs = useCallback(() => {
        let index = 0;
        intervalRef.current = setInterval(() => {
            if (index < mockAgentLogs.length) {
                setLogs((prev) => [...prev, mockAgentLogs[index]]);
                index++;
            } else if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        }, 400);
    }, []);

    /** Simulates progress through audit stages during mock mode. */
    const simulateStages = useCallback(() => {
        const delays = [0, 1500, 3000, 4500, 6000];
        delays.forEach((delay, i) => {
            setTimeout(() => {
                setStages((prev) =>
                    prev.map((stage, idx) => ({
                        ...stage,
                        status:
                            idx < i
                                ? "completed"
                                : idx === i
                                    ? "running"
                                    : stage.status,
                    }))
                );
            }, delay);
        });

        // Mark all completed
        setTimeout(() => {
            setStages((prev) =>
                prev.map((stage) => ({ ...stage, status: "completed" as const }))
            );
        }, 7500);
    }, []);

    /** Starts an audit with the given input configuration. */
    const startAudit = useCallback(
        async (input: AuditInput) => {
            try {
                setStatus("running");
                setError(null);
                setLogs([]);
                setStages(defaultAuditStages.map((s) => ({ ...s, status: "pending" as const })));

                simulateLogs();
                simulateStages();

                const auditResult = await submitAudit(input);
                setResult(auditResult);
                setStatus("completed");
            } catch (err) {
                setError(err instanceof Error ? err.message : "Audit failed");
                setStatus("failed");
            } finally {
                if (intervalRef.current) {
                    clearInterval(intervalRef.current);
                }
            }
        },
        [simulateLogs, simulateStages]
    );

    /** Resets all audit state to initial values. */
    const reset = useCallback(() => {
        setStatus("idle");
        setStages(defaultAuditStages);
        setLogs([]);
        setResult(null);
        setError(null);
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
        }
    }, []);

    return { status, stages, logs, result, error, startAudit, reset };
}
