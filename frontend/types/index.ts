/**
 * TypeScript type definitions for the Multi-Agent Code Auditor frontend.
 */

/** Possible statuses for an audit run. */
export type AuditStatus = "idle" | "pending" | "running" | "completed" | "failed";

/** Severity levels for findings — mirrors the backend's 4-level scale. */
export type Severity = "critical" | "high" | "medium" | "low";

/** Categories for findings. */
export type FindingCategory = "security" | "performance" | "code-quality" | "suggestion";

/** Input modes for submitting an audit. */
export type AuditInputMode = "github" | "upload" | "paste";

/** Supported programming languages for the paste mode. */
export type ProgrammingLanguage = "python" | "javascript" | "typescript" | "java";

/** A single finding from an audit analysis, normalized from the backend's
 * raw {issue, explanation, suggested_fix, before_code, after_code, agent,
 * severity, cwe} shape — see lib/findings.ts. */
export interface Finding {
    id: string;
    category: FindingCategory;
    severity: Severity;
    title: string;
    description: string;
    file: string;
    /** 1-based line in the file. Exact for static-analysis findings; for LLM
     * findings it's set only when the quoted code was found in the source,
     * so a missing line means "couldn't verify", never a guess. */
    line?: number;
    /** Who reported it: "llm", "bandit", "ruff", "semgrep", or e.g. "bandit+llm". */
    source?: string;
    /** Rule identifier from a static analyzer (e.g. "B608", "F821"). */
    ruleId?: string;
    codeSnippet: string;
    suggestedFix: string;
    agent: string;
    cwe?: string;
    before_code?: string;
    after_code?: string;
}

/** A log entry produced by an agent during an audit. */
export interface AgentLog {
    id: string;
    timestamp: string;
    agent: string;
    message: string;
    level: "info" | "warning" | "error" | "success";
}

/** A metric data point displayed on the dashboard. */
export interface MetricData {
    label: string;
    value: number;
    trend: number;
    trendDirection: "up" | "down";
    icon: string;
}

/** A data point for the vulnerability trend chart. */
export interface TrendPoint {
    date: string;
    critical: number;
    warning: number;
    info: number;
}

/** A single row in the recent audits list. */
export interface RecentAudit {
    id: string;
    repository: string;
    date: string;
    status: AuditStatus;
    findings: number;
    /** Files whose audit errored/timed out, even if the job as a whole
     * "completed" — distinguishes a genuinely clean result from one where
     * nothing was actually analyzed. */
    files_errored?: number;
}

/** The full result of an audit run. */
export interface AuditResult {
    id: string;
    repository: string;
    status: AuditStatus;
    startedAt: string;
    completedAt: string | null;
    findings: Finding[];
    logs: AgentLog[];
    summary: string;
}

/** The input data for starting a new audit. */
export interface AuditInput {
    mode: AuditInputMode;
    githubUrl?: string;
    files?: File[];
    code?: string;
    language?: ProgrammingLanguage;
    /** quick = Security agent only; full = all agents. */
    depth?: "quick" | "full";
}

/** Represents an agent node in the agent graph. */
export interface AgentNode {
    id: string;
    label: string;
    type: "manager" | "analyzer" | "reviewer";
    status: "idle" | "running" | "completed";
}

/** Represents an agent stage in the progress indicator. */
export interface AuditStage {
    id: number;
    label: string;
    status: "pending" | "running" | "completed" | "error";
}
