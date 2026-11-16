import { expect, test } from "@playwright/test";
import { API, fakeBasics, json } from "./fake-backend";

/**
 * Wait until React has taken over (hydrated) the login form. Typing before
 * that gets reset when React attaches, leaving the required fields empty so
 * the browser silently refuses to submit (seen after the 401 redirect on
 * slower machines).
 */
async function readyLoginForm(page: import("@playwright/test").Page) {
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("button", { name: "Sign in" })).toBeEnabled();
}

test("a 401 sends you to login, and signing in brings you back", async ({ page }) => {
    await fakeBasics(page);
    let loggedIn = false;
    let loginBody: Record<string, unknown> = {};
    await page.route(`${API}/audit/history?*`, (route) =>
        loggedIn ? json(route, []) : json(route, { detail: "Not authenticated" }, 401)
    );
    await page.route(`${API}/auth/login`, async (route) => {
        loginBody = route.request().postDataJSON();
        loggedIn = true;
        await json(route, { authenticated: true, auth_enabled: true, username: "admin" });
    });

    await page.goto("/history");
    await expect(page).toHaveURL(/\/login\?next=%2Fhistory$/);

    await readyLoginForm(page);
    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Password").fill("correct horse battery staple");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/history$/);
    expect(loginBody).toEqual({ username: "admin", password: "correct horse battery staple" });
});

test("wrong password and rate limit show clear messages", async ({ page }) => {
    await fakeBasics(page);
    let attempts = 0;
    await page.route(`${API}/auth/login`, (route) => {
        attempts += 1;
        return attempts === 1
            ? json(route, { detail: "Wrong username or password" }, 401)
            : json(route, { detail: "Too many login attempts" }, 429);
    });

    await page.goto("/login");
    await readyLoginForm(page);
    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Password").fill("nope");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Wrong username" })).toHaveText("Wrong username or password.");

    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Too many" })).toHaveText("Too many attempts. Wait a minute and try again.");
    await expect(page).toHaveURL(/\/login$/);
});

test("login never redirects to another site", async ({ page }) => {
    await fakeBasics(page);
    await page.route(`${API}/auth/login`, (route) => json(route, { authenticated: true }));

    await page.goto("/login?next=//evil.example.com/steal");
    await readyLoginForm(page);
    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Password").fill("whatever-password");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL("http://localhost:3000/");
});

// "/" + backslash + "evil..." — browsers treat the backslash like "/".
for (const next of ["/" + "\\" + "evil.example.com/steal", "https://evil.example.com/", "/login?next=/history"]) {
    test(`login ignores unsafe return address ${JSON.stringify(next)}`, async ({ page }) => {
        await fakeBasics(page);
        await page.route(`${API}/auth/login`, (route) => json(route, { authenticated: true }));

        await page.goto(`/login?next=${encodeURIComponent(next)}`);
        await readyLoginForm(page);
        await page.getByLabel("Username").fill("admin");
        await page.getByLabel("Password").fill("whatever-password");
        await page.getByRole("button", { name: "Sign in" }).click();

        await expect(page).toHaveURL("http://localhost:3000/");
    });
}

test("login keeps a safe return address including its query", async ({ page }) => {
    await fakeBasics(page);
    await page.route(`${API}/auth/login`, (route) => json(route, { authenticated: true }));
    await page.route(`${API}/audit/history?*`, (route) => json(route, []));

    await page.goto(`/login?next=${encodeURIComponent("/history?page=2")}`);
    await readyLoginForm(page);
    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Password").fill("whatever-password");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL("http://localhost:3000/history?page=2");
});
