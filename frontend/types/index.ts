/**
 * TypeScript type definitions for the Multi-Agent Code Auditor frontend.
 */

/** Possible statuses for an audit run. */
export type AuditStatus = "idle" | "running" | "completed" | "failed";

/** Severity levels for findings. */
export type Severity = "critical" | "warning" | "info";

/** Categories for findings. */
export type FindingCategory = "security" | "performance" | "code-quality" | "suggestion";

/** Input modes for submitting an audit. */
export type AuditInputMode = "github" | "upload" | "paste";

/** Supported programming languages for the paste mode. */
export type ProgrammingLanguage = "python" | "javascript" | "typescript" | "java";

/** A single finding from an audit analysis. */
export interface Finding {
    id: string;
    category: FindingCategory;
    severity: Severity;
    title: string;
    description: string;
    file: string;
    line: number;
    codeSnippet: string;
    suggestedFix: string;
    agent: string;
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
