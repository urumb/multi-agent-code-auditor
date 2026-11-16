import { expect, test } from "@playwright/test";
import { API, fakeBasics, json } from "./fake-backend";

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
    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Password").fill("nope");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toHaveText("Wrong username or password.");

    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toHaveText("Too many attempts. Wait a minute and try again.");
    await expect(page).toHaveURL(/\/login$/);
});

test("login never redirects to another site", async ({ page }) => {
    await fakeBasics(page);
    await page.route(`${API}/auth/login`, (route) => json(route, { authenticated: true }));

    await page.goto("/login?next=//evil.example.com/steal");
    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Password").fill("whatever-password");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL("http://localhost:3000/");
});
