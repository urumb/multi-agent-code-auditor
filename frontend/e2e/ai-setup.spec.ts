import { expect, test } from "@playwright/test";
import { API, aiStatus, fakeBasics, json } from "./fake-backend";

test("no setup card when AI is ready", async ({ page }) => {
    await fakeBasics(page);
    await page.goto("/audit");
    await expect(page.getByRole("button", { name: "Run Audit" })).toBeVisible();
    await expect(page.getByRole("region", { name: "AI setup" })).toHaveCount(0);
});

test("Ollama not running: offers install link and tools-only mode", async ({ page }) => {
    await fakeBasics(page);
    let aiOn = true;
    let saved: Record<string, unknown> | null = null;
    await page.route(`${API}/settings/status`, (r) =>
        json(r, aiStatus({ ai_enabled: aiOn, ollama_reachable: false, model_installed: false, models: [] }))
    );
    await page.route(`${API}/settings`, async (r) => {
        saved = r.request().postDataJSON();
        aiOn = false;
        return json(r, { status: "ok", ai_enabled: false });
    });

    await page.goto("/audit");
    const card = page.getByRole("region", { name: "AI setup" });
    await expect(card.getByText("AI agents need Ollama")).toBeVisible();
    await expect(card.getByRole("link", { name: "Get Ollama" })).toHaveAttribute("href", "https://ollama.com/download");

    await card.getByRole("button", { name: "Use tools-only" }).click();
    await expect(card).toHaveCount(0);
    expect(saved).toEqual({ ai_enabled: false });
});

test("model missing: one-click download with progress", async ({ page }) => {
    await fakeBasics(page);
    let phase: "missing" | "pulling" | "done" = "missing";
    let polls = 0;
    let pulled = "";
    await page.route(`${API}/settings/status`, (r) => {
        if (phase === "pulling" && ++polls >= 3) phase = "done";
        if (phase === "missing") return json(r, aiStatus({ model_installed: false, models: [] }));
        if (phase === "pulling") {
            return json(r, aiStatus({
                model_installed: false,
                pull: { model: "qwen2.5-coder:3b", status: "pulling", completed: 50, total: 100, error: null },
            }));
        }
        return json(r, aiStatus({ pull: { model: "qwen2.5-coder:3b", status: "done", completed: 100, total: 100, error: null } }));
    });
    await page.route(`${API}/settings/models/pull`, async (r) => {
        pulled = r.request().postDataJSON().model;
        phase = "pulling";
        return json(r, { model: pulled, status: "pulling", completed: 0, total: 0, error: null });
    });

    await page.goto("/audit");
    const card = page.getByRole("region", { name: "AI setup" });
    await card.getByRole("button", { name: "Download qwen2.5-coder:3b" }).click();
    await expect(card.getByText("Downloading qwen2.5-coder:3b... 50%")).toBeVisible();
    await expect(card).toHaveCount(0, { timeout: 10_000 }); // disappears when the download finishes
    expect(pulled).toBe("qwen2.5-coder:3b");
});
