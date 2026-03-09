import type {
    Finding,
    AgentLog,
    MetricData,
    TrendPoint,
    RecentAudit,
    AuditResult,
    AuditStage,
} from "@/types";

/** Dashboard metric cards data. */
export const mockMetrics: MetricData[] = [
    {
        label: "Repositories Scanned",
        value: 142,
        trend: 12,
        trendDirection: "up",
        icon: "folder-git-2",
    },
    {
        label: "Vulnerabilities Found",
        value: 38,
        trend: -5,
        trendDirection: "down",
        icon: "shield-alert",
    },
    {
        label: "Code Quality Issues",
        value: 67,
        trend: 8,
        trendDirection: "up",
        icon: "bug",
    },
    {
        label: "Performance Warnings",
        value: 23,
        trend: -3,
        trendDirection: "down",
        icon: "gauge",
    },
];

/** Vulnerability trend data for the chart. */
export const mockTrendData: TrendPoint[] = [
    { date: "Jan", critical: 4, warning: 12, info: 20 },
    { date: "Feb", critical: 6, warning: 10, info: 18 },
    { date: "Mar", critical: 3, warning: 14, info: 22 },
    { date: "Apr", critical: 8, warning: 9, info: 16 },
    { date: "May", critical: 5, warning: 11, info: 24 },
    { date: "Jun", critical: 2, warning: 13, info: 19 },
    { date: "Jul", critical: 7, warning: 8, info: 21 },
    { date: "Aug", critical: 3, warning: 15, info: 17 },
];

/** Recent audit history. */
export const mockRecentAudits: RecentAudit[] = [
    {
        id: "aud-001",
        repository: "acme/payment-service",
        date: "2026-03-09T10:30:00Z",
        status: "completed",
        findings: 12,
    },
    {
        id: "aud-002",
        repository: "acme/auth-gateway",
        date: "2026-03-09T09:15:00Z",
        status: "running",
        findings: 0,
    },
    {
        id: "aud-003",
        repository: "acme/data-pipeline",
        date: "2026-03-08T16:45:00Z",
        status: "completed",
        findings: 7,
    },
    {
        id: "aud-004",
        repository: "acme/user-dashboard",
        date: "2026-03-08T14:20:00Z",
        status: "failed",
        findings: 0,
    },
    {
        id: "aud-005",
        repository: "acme/notification-svc",
        date: "2026-03-07T11:10:00Z",
        status: "completed",
        findings: 3,
    },
];

/** Mock findings that mirror the backend analysis structure. */
export const mockFindings: Finding[] = [
    {
        id: "f-001",
        category: "security",
        severity: "critical",
        title: "SQL Injection Vulnerability",
        description:
            "User input is directly concatenated into SQL query without parameterization. An attacker could execute arbitrary SQL commands.",
        file: "src/db/queries.py",
        line: 42,
        codeSnippet: `query = f"SELECT * FROM users WHERE id = '{user_id}'"`,
        suggestedFix: `query = "SELECT * FROM users WHERE id = %s"\ncursor.execute(query, (user_id,))`,
        agent: "Security Agent",
    },
    {
        id: "f-002",
        category: "security",
        severity: "critical",
        title: "Hardcoded Secret Key",
        description:
            "A secret API key is hardcoded in the source file. This exposes credentials in version control.",
        file: "src/config.py",
        line: 15,
        codeSnippet: `SECRET_KEY = "sk-live-a1b2c3d4e5f6g7h8i9j0"`,
        suggestedFix: `import os\nSECRET_KEY = os.environ.get("SECRET_KEY")`,
        agent: "Security Agent",
    },
    {
        id: "f-003",
        category: "security",
        severity: "warning",
        title: "Missing Input Validation",
        description:
            "The endpoint accepts user input without validation, potentially allowing crafted payloads.",
        file: "src/api/routes.py",
        line: 78,
        codeSnippet: `@app.post("/upload")\nasync def upload(data: dict):`,
        suggestedFix: `from pydantic import BaseModel\n\nclass UploadRequest(BaseModel):\n    filename: str\n    content: str\n\n@app.post("/upload")\nasync def upload(data: UploadRequest):`,
        agent: "Security Agent",
    },
    {
        id: "f-004",
        category: "performance",
        severity: "warning",
        title: "N+1 Query Pattern",
        description:
            "Database query inside a loop causes N+1 problem. Consider using a batch query or JOIN.",
        file: "src/services/user_service.py",
        line: 55,
        codeSnippet: `for user in users:\n    orders = db.query(Order).filter(Order.user_id == user.id).all()`,
        suggestedFix: `user_ids = [u.id for u in users]\norders = db.query(Order).filter(Order.user_id.in_(user_ids)).all()`,
        agent: "Performance Agent",
    },
    {
        id: "f-005",
        category: "performance",
        severity: "info",
        title: "Unnecessary Data Fetching",
        description:
            "Fetching all columns when only a subset is needed. Use column projection to reduce memory usage.",
        file: "src/services/analytics.py",
        line: 30,
        codeSnippet: `results = db.query(Event).all()`,
        suggestedFix: `results = db.query(Event.id, Event.type, Event.created_at).all()`,
        agent: "Performance Agent",
    },
    {
        id: "f-006",
        category: "code-quality",
        severity: "warning",
        title: "Missing Error Handling",
        description:
            "No try-except block around external API call. Unhandled exceptions will crash the service.",
        file: "src/integrations/slack.py",
        line: 22,
        codeSnippet: `response = requests.post(webhook_url, json=payload)`,
        suggestedFix: `try:\n    response = requests.post(webhook_url, json=payload)\n    response.raise_for_status()\nexcept requests.RequestException as e:\n    logger.error(f"Slack notification failed: {e}")`,
        agent: "Code Quality Agent",
    },
    {
        id: "f-007",
        category: "code-quality",
        severity: "info",
        title: "Magic Number Detected",
        description:
            "Numeric literal used without explanation. Extract to a named constant for readability.",
        file: "src/utils/helpers.py",
        line: 88,
        codeSnippet: `if retries > 3:`,
        suggestedFix: `MAX_RETRIES = 3\nif retries > MAX_RETRIES:`,
        agent: "Code Quality Agent",
    },
    {
        id: "f-008",
        category: "suggestion",
        severity: "info",
        title: "Consider Using Async/Await",
        description:
            "Synchronous HTTP calls block the event loop. Use async variants for better throughput.",
        file: "src/services/external_api.py",
        line: 14,
        codeSnippet: `response = requests.get(api_url)`,
        suggestedFix: `import httpx\n\nasync with httpx.AsyncClient() as client:\n    response = await client.get(api_url)`,
        agent: "Reviewer Agent",
    },
];

/** Simulated agent log stream. */
export const mockAgentLogs: AgentLog[] = [
    { id: "l-01", timestamp: "12:01:23", agent: "Manager Agent", message: "Starting repository decomposition", level: "info" },
    { id: "l-02", timestamp: "12:01:25", agent: "Manager Agent", message: "Identified 14 source files for analysis", level: "success" },
    { id: "l-03", timestamp: "12:01:27", agent: "Security Agent", message: "Scanning dependencies for known CVEs", level: "info" },
    { id: "l-04", timestamp: "12:01:30", agent: "Security Agent", message: "Checking for injection vulnerabilities", level: "info" },
    { id: "l-05", timestamp: "12:01:33", agent: "Security Agent", message: "⚠ SQL injection vulnerability detected in queries.py", level: "warning" },
    { id: "l-06", timestamp: "12:01:35", agent: "Security Agent", message: "⚠ Hardcoded secret detected in config.py", level: "warning" },
    { id: "l-07", timestamp: "12:01:38", agent: "Performance Agent", message: "Analyzing query patterns", level: "info" },
    { id: "l-08", timestamp: "12:01:41", agent: "Performance Agent", message: "⚠ N+1 query pattern found in user_service.py", level: "warning" },
    { id: "l-09", timestamp: "12:01:44", agent: "Code Quality Agent", message: "Running linting and style checks", level: "info" },
    { id: "l-10", timestamp: "12:01:47", agent: "Code Quality Agent", message: "Missing error handling in slack.py", level: "warning" },
    { id: "l-11", timestamp: "12:01:50", agent: "Reviewer Agent", message: "Aggregating findings from all agents", level: "info" },
    { id: "l-12", timestamp: "12:01:53", agent: "Reviewer Agent", message: "Generating remediation suggestions", level: "info" },
    { id: "l-13", timestamp: "12:01:56", agent: "Reviewer Agent", message: "✓ Audit complete — 8 findings generated", level: "success" },
];

/** Mock full audit result. */
export const mockAuditResult: AuditResult = {
    id: "aud-001",
    repository: "acme/payment-service",
    status: "completed",
    startedAt: "2026-03-09T10:30:00Z",
    completedAt: "2026-03-09T10:32:00Z",
    findings: mockFindings,
    logs: mockAgentLogs,
    summary:
        "Audit completed successfully. Found 2 critical security vulnerabilities, 3 warnings, and 3 informational suggestions across 14 files.",
};

/** Default audit stages for the progress indicator. */
export const defaultAuditStages: AuditStage[] = [
    { id: 1, label: "Repository Decomposition", status: "pending" },
    { id: 2, label: "Security Analysis", status: "pending" },
    { id: 3, label: "Performance Analysis", status: "pending" },
    { id: 4, label: "Code Quality Analysis", status: "pending" },
    { id: 5, label: "Reviewer Agent Summary", status: "pending" },
];
