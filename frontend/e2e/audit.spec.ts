import { expect, test } from "@playwright/test";
import { API, SQL_FINDING, fakeBasics, json, report, sse } from "./fake-backend";

const CODE = "def get(conn, name):\n    query = \"SELECT * FROM users WHERE name = '%s'\" % name\n";

async function startPasteAudit(page: import("@playwright/test").Page) {
    await page.goto("/audit");
    await page.getByRole("button", { name: "Paste" }).click();
    await page.getByPlaceholder("Paste your code here...").fill(CODE);
    await page.getByRole("button", { name: "quick" }).click();
    await page.getByRole("button", { name: "Run Audit" }).click();
}

test("paste audit streams a result that opens on the Results page", async ({ page }) => {
    await fakeBasics(page);
    let requestBody: Record<string, unknown> = {};
    await page.route(`${API}/audit/stream`, async (route) => {
        requestBody = route.request().postDataJSON();
        await json(route, { job_id: "job-1" });
    });
    await page.route(`${API}/audit/stream/job-1`, (route) =>
        route.fulfill({
            status: 200,
            contentType: "text/event-stream",
            body: sse([
                { type: "file_start", data: { path: "pasted_input.py", index: 1, total: 1 } },
                { type: "log", data: { agent: "System", message: "Processing", level: "info" } },
                {
                    type: "result",
                    data: {
                        file_path: "pasted_input.py",
                        final_report: report([SQL_FINDING]),
                        risk_score: 7,
                        max_severity: "High",
                        error: null,
                        cached: false,
                    },
                },
                { type: "done", data: { total_files: 1, duration: 1.5 } },
            ]),
        })
    );

    await startPasteAudit(page);
    await expect(page.getByText("Completed in 1.5s")).toBeVisible();
    expect(requestBody).toMatchObject({ input_type: "paste", depth: "quick" });

    await page.goto("/results");
    await expect(page.getByText("1 file(s) audited")).toBeVisible();
    await expect(page.getByText("report ready")).toBeVisible();
    await expect(page.getByRole("link", { name: "Export SARIF" })).toHaveAttribute(
        "href",
        `${API}/audit/history/job-1/sarif`
    );

    await page.getByText("pasted_input.py").first().click();
    await expect(page.getByText("SQL injection")).toBeVisible();
    await expect(page.getByText("bandit + AI · B608")).toBeVisible();
    await expect(page.getByText("pasted_input.py:6")).toBeVisible();
});

test("cancelling a running audit keeps finished files", async ({ page }) => {
    await fakeBasics(page);
    let releaseStream: () => void = () => {};
    const cancelled = new Promise<void>((resolve) => (releaseStream = resolve));
    let cancelCalls = 0;

    await page.route(`${API}/audit/stream`, (route) => json(route, { job_id: "job-2" }));
    await page.route(`${API}/audit/stream/job-2/cancel`, async (route) => {
        cancelCalls += 1;
        await json(route, { status: "cancelling" });
        releaseStream();
    });
    // The stream only answers once the user has clicked Cancel, so the UI
    // stays in the "running" state until then.
    await page.route(`${API}/audit/stream/job-2`, async (route) => {
        await cancelled;
        await route.fulfill({
            status: 200,
            contentType: "text/event-stream",
            body: sse([
                {
                    type: "result",
                    data: {
                        file_path: "a.py",
                        final_report: report([]),
                        risk_score: 0,
                        max_severity: "Low",
                        error: null,
                    },
                },
                { type: "cancelled", data: { files_done: 1, total_files: 3, duration: 2 } },
            ]),
        });
    });

    await startPasteAudit(page);
    await page.getByRole("button", { name: "Cancel audit" }).click();
    await expect(page.getByText("Audit cancelled after 1 of 3 file(s)")).toBeVisible();
    expect(cancelCalls).toBe(1);
    await expect(page.getByRole("button", { name: "Cancel audit" })).toHaveCount(0);

    await page.goto("/results");
    await expect(page.getByText("This audit was cancelled.")).toBeVisible();
    await expect(page.getByText("cancelled", { exact: true })).toBeVisible();
});

test("files reused from a previous audit are marked unchanged", async ({ page }) => {
    await fakeBasics(page);
    await page.addInitScript((stored) => window.localStorage.setItem("latestAuditResult", stored), JSON.stringify({
        job_id: "job-3",
        total_files: 1,
        results: [{
            file_path: "same.py", final_report: report([]), risk_score: 0,
            max_severity: "Low", error: null, cached: true,
        }],
    }));
    await page.goto("/results");
    await expect(page.getByText("same.py")).toBeVisible();
    await expect(page.getByText("unchanged", { exact: true })).toBeVisible();
});

test("history shows an incomplete audit's warning", async ({ page }) => {
    await fakeBasics(page);
    const warning = "Security Agent: AI analysis failed for 1 of 1 chunk(s) (Ollama isn't reachable; is it running?).";
    await page.route(`${API}/audit/history?*`, (route) => json(route, [{
        id: "abc", repository: "Pasted Code", date: "2026-11-16T10:00:00", status: "completed",
        findings: 1, max_severity: "High", duration: 3.2, input_type: "paste", files_errored: 0,
    }]));
    await page.route(`${API}/audit/history/abc`, (route) => json(route, {
        id: "abc", repository: "Pasted Code", status: "completed", input_type: "paste",
        created_at: 1794800000, duration: 3.2, error: null, total_files: 1, files_skipped: 0,
        results: [{
            file_path: "pasted_input.py", final_report: report([SQL_FINDING], { warnings: [warning] }),
            risk_score: 7, max_severity: "High", error: null,
        }],
    }));

    await page.goto("/history");
    await page.getByText("Pasted Code").first().click();
    await expect(page).toHaveURL(/\/history\/abc$/);
    await page.getByText("pasted_input.py").first().click();
    await expect(page.getByText("This audit is incomplete")).toBeVisible();
    await expect(page.getByText(warning, { exact: false })).toBeVisible();
    await expect(page.getByRole("link", { name: "Export SARIF" })).toHaveAttribute(
        "href",
        `${API}/audit/history/abc/sarif`
    );
});
