import type { NextConfig } from "next";

// This project never sends data off your machine, so Next.js's anonymous
// usage telemetry is switched off for everyone who builds or runs it. Next
// reads this when it starts telemetry, which happens after loading this file
// (for both `next build` and `next dev`). Set NEXT_TELEMETRY_DISABLED=0 in
// your environment to opt back in.
if (!process.env.NEXT_TELEMETRY_DISABLED) {
    process.env.NEXT_TELEMETRY_DISABLED = "1";
}

const nextConfig: NextConfig = {
  /* config options here */
};

export default nextConfig;
