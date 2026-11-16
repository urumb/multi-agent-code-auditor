import { defineConfig, devices } from "@playwright/test";

/**
 * Browser tests for the UI. The backend is faked inside the browser
 * (see e2e/fake-backend.ts), so no Python backend or Ollama is needed and
 * results are deterministic.
 *
 * Run locally (build first; uses the production server):
 *   npm install --no-save @playwright/test@1.64.1
 *   npx playwright install chromium
 *   npm run build && npx playwright test
 */
export default defineConfig({
    testDir: "./e2e",
    timeout: 30_000,
    retries: process.env.CI ? 1 : 0,
    reporter: "list",
    use: {
        baseURL: "http://localhost:3000",
        trace: "retain-on-failure",
    },
    projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
    webServer: {
        command: "npm run start",
        url: "http://localhost:3000",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
    },
});
