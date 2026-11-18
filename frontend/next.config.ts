import type { NextConfig } from "next";

// This project never sends data off your machine, so Next.js's anonymous
// usage telemetry is switched off for everyone who builds or runs it. Next
// reads this when it starts telemetry, which happens after loading this file
// (for both `next build` and `next dev`). Set NEXT_TELEMETRY_DISABLED=0 in
// your environment to opt back in.
if (!process.env.NEXT_TELEMETRY_DISABLED) {
    process.env.NEXT_TELEMETRY_DISABLED = "1";
}

// Desktop build (npm run build:desktop): plain HTML/JS files in out/, served
// by the Python backend inside the desktop app. trailingSlash makes each page
// a folder with index.html (/history/view/index.html), which a simple static
// file server can serve without rewrites. The normal web build is unchanged.
const desktopExport = process.env.NEXT_OUTPUT === "export";

const nextConfig: NextConfig = {
  ...(desktopExport ? { output: "export" as const, trailingSlash: true } : {}),
};

export default nextConfig;
