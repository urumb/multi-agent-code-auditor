// Build the static UI for the desktop app (frontend/out).
//
// - NEXT_OUTPUT=export     -> plain HTML/JS files (see next.config.ts)
// - NEXT_PUBLIC_API_URL=/api -> the UI calls the API on the same address,
//   where the desktop app's backend serves it
//
// A script instead of inline env vars in package.json, because
// `VAR=value cmd` doesn't work in Windows shells.
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const nextBin = require.resolve("next/dist/bin/next");

const result = spawnSync(process.execPath, [nextBin, "build"], {
    stdio: "inherit",
    env: { ...process.env, NEXT_OUTPUT: "export", NEXT_PUBLIC_API_URL: "/api" },
});
process.exit(result.status ?? 1);
