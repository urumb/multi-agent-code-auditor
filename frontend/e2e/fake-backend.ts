import type { Page, Route } from "@playwright/test";

/** Where the UI expects the backend (the default NEXT_PUBLIC_API_URL). */
export const API = "http://localhost:8000";

export interface FakeFinding {
    severity: string;
    issue: string;
    agent: string;
    line?: number | null;
    source?: string;
    rule_id?: string;
    explanation?: string;
    suggested_fix?: string;
    before_code?: string;
    after_code?: string;
}

export function report(findings: FakeFinding[], extra: Record<string, unknown> = {}): string {
    return JSON.stringify({
        "Executive Summary": "Fake summary for the browser tests.",
        "Findings Summary": `${findings.length} finding(s).`,
        risk_score: findings.length ? 7 : 0,
        max_severity: findings[0]?.severity ?? "Low",
        findings,
        top_risk_files: [],
        ...extra,
    });
}

export const SQL_FINDING: FakeFinding = {
    severity: "High",
    issue: "SQL injection",
    agent: "security",
    line: 6,
    source: "bandit+llm",
    rule_id: "B608",
    explanation: "User input is formatted into the SQL query.",
    suggested_fix: "Use a parameterized query.",
    before_code: "query = \"SELECT * FROM users WHERE name = '%s'\" % name",
    after_code: "conn.execute(\"SELECT * FROM users WHERE name = ?\", (name,))",
};

/** Server-Sent Events body, as the backend streams it. */
export function sse(events: { type: string; data: unknown }[]): string {
    return events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");
}

export function json(route: Route, body: unknown, status = 200) {
    return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

/** Answers the background polling every page does (health, notifications). */
export async function fakeBasics(page: Page) {
    await page.route(`${API}/health`, (r) => json(r, { status: "ok" }));
    await page.route(`${API}/recent-audits`, (r) => json(r, []));
    await page.route(`${API}/metrics`, (r) => json(r, []));
    await page.route(`${API}/trends`, (r) => json(r, []));
    // AI ready by default, so the setup card stays hidden unless a test says otherwise.
    await page.route(`${API}/settings/status`, (r) => json(r, aiStatus()));
}

export function aiStatus(overrides: Record<string, unknown> = {}) {
    return {
        ai_enabled: true,
        ollama_reachable: true,
        model: "qwen2.5-coder:3b",
        model_installed: true,
        models: ["qwen2.5-coder:3b"],
        pull: { model: null, status: "idle", completed: 0, total: 0, error: null },
        ...overrides,
    };
}
