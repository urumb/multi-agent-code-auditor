import type { Finding, FindingCategory, Severity } from "@/types";

/** Raw finding shape as produced by the backend (src/findings.py Finding model). */
export interface RawFinding {
    severity?: string;
    issue?: string;
    explanation?: string;
    suggested_fix?: string;
    before_code?: string;
    after_code?: string;
    cwe?: string;
    agent?: string;
    snippet_index?: number;
    line?: number | null;
    source?: string;
    rule_id?: string;
}

const SEVERITY_MAP: Record<string, Severity> = {
    critical: "critical",
    high: "high",
    medium: "medium",
    low: "low",
};

const CATEGORY_MAP: Record<string, FindingCategory> = {
    security: "security",
    performance: "performance",
    quality: "code-quality",
};

/**
 * Normalizes one backend finding into the frontend's Finding shape.
 *
 * The backend emits {issue, explanation, suggested_fix, agent, severity: 4-level,
 * ...} — this maps field names and the severity scale so IssueCard/SeverityBadge/
 * ResultTabs (which filter by `category`) actually receive the fields they expect.
 */
export function mapFinding(raw: RawFinding, index: number, filePath: string): Finding {
    const agent = (raw.agent || "").toLowerCase();
    return {
        id: `${filePath}-${index}-${raw.issue ?? "finding"}`,
        category: CATEGORY_MAP[agent] ?? "suggestion",
        severity: SEVERITY_MAP[(raw.severity || "low").toLowerCase()] ?? "low",
        title: raw.issue || "Untitled finding",
        description: raw.explanation || "",
        file: filePath,
        codeSnippet: raw.before_code || "",
        suggestedFix: raw.suggested_fix || "",
        agent: raw.agent ? raw.agent.charAt(0).toUpperCase() + raw.agent.slice(1) : "Unknown",
        cwe: raw.cwe || undefined,
        line: raw.line ?? undefined,
        source: raw.source || undefined,
        ruleId: raw.rule_id || undefined,
        before_code: raw.before_code || "",
        after_code: raw.after_code || "",
    };
}

const LANGUAGE_BY_EXTENSION: Record<string, string> = {
    py: "python", js: "javascript", jsx: "jsx", ts: "typescript", tsx: "tsx",
    java: "java", go: "go", rb: "ruby", php: "php", rs: "rust", cs: "csharp",
    c: "c", h: "c", cpp: "cpp", hpp: "cpp", kt: "kotlin", swift: "swift",
    sh: "bash", sql: "sql",
};

/** Syntax-highlighting language for a file path (falls back to plain text). */
export function languageForFile(filePath: string): string {
    const ext = filePath.split(".").pop()?.toLowerCase() ?? "";
    return LANGUAGE_BY_EXTENSION[ext] ?? "text";
}

/** Human label for who reported a finding, e.g. "bandit + AI". */
export function sourceLabel(source?: string): string {
    if (!source) return "AI";
    return source
        .split("+")
        .map((s) => (s === "llm" ? "AI" : s))
        .join(" + ");
}

export function mapFindings(raw: RawFinding[] | undefined, filePath: string): Finding[] {
    return (raw || []).map((f, i) => mapFinding(f, i, filePath));
}
