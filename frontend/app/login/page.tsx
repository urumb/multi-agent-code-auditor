"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Lock } from "lucide-react";
import { login } from "@/lib/api";

/**
 * Where to go after signing in: only a page on this site, never another one.
 * The address is resolved exactly as the browser would resolve it, so tricks
 * like "//evil.com" or "/" + backslash + "evil.com" (browsers treat a
 * backslash like "/") end up
 * on another origin and are rejected.
 */
function safeNext(raw: string | null): string {
    if (!raw) return "/";
    try {
        const url = new URL(raw, window.location.origin);
        if (url.origin !== window.location.origin || url.pathname.startsWith("/login")) return "/";
        return url.pathname + url.search + url.hash;
    } catch {
        return "/";
    }
}

/**
 * Login page. Shown only when the backend has login enabled
 * (AUTH_ENABLED=true); other pages are sent here on a 401.
 */
export default function LoginPage() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);
    const router = useRouter();

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        setSubmitting(true);
        setError(null);
        try {
            const problem = await login(username, password);
            if (problem) {
                setError(problem);
                return;
            }
            const next = new URLSearchParams(window.location.search).get("next");
            router.replace(safeNext(next));
        } catch {
            setError("Can't reach the server. Try again in a moment.");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="mx-auto mt-16 max-w-sm">
            <form onSubmit={handleSubmit} className="glass-card space-y-5 p-6">
                <div className="flex items-center gap-2">
                    <Lock className="h-4 w-4 text-primary" />
                    <h1 className="text-lg font-semibold text-foreground">Sign in</h1>
                </div>
                <div className="space-y-2">
                    <label htmlFor="username" className="text-sm font-medium text-foreground">
                        Username
                    </label>
                    <input
                        id="username"
                        autoComplete="username"
                        required
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        className="w-full rounded-lg border border-border bg-muted/30 px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                    />
                </div>
                <div className="space-y-2">
                    <label htmlFor="password" className="text-sm font-medium text-foreground">
                        Password
                    </label>
                    <input
                        id="password"
                        type="password"
                        autoComplete="current-password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full rounded-lg border border-border bg-muted/30 px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                    />
                </div>
                {error && (
                    <p role="alert" className="text-sm text-red-400">
                        {error}
                    </p>
                )}
                <button
                    type="submit"
                    disabled={submitting}
                    className="w-full rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                    {submitting ? "Signing in..." : "Sign in"}
                </button>
            </form>
        </div>
    );
}
