"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { Bell, ShieldAlert, CheckCircle2, XCircle, ArrowUpRight, Menu, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { checkBackendHealth, fetchRecentAudits } from "@/lib/api";
import type { RecentAudit } from "@/types";
import { cn } from "@/lib/utils";

const HEALTH_POLL_MS = 20_000;
const NOTIF_POLL_MS = 30_000;
const READ_STORAGE_KEY = "readAuditNotifications";

const navItems = [
    { href: "/", label: "Overview" },
    { href: "/audit", label: "Audit" },
    { href: "/results", label: "Results" },
    { href: "/history", label: "History" },
    { href: "/agents", label: "Agents" },
    { href: "/settings", label: "Settings" },
];

function iconFor(status: RecentAudit["status"]): { Icon: LucideIcon; color: string } {
    if (status === "failed") return { Icon: XCircle, color: "text-red-400" };
    if (status === "completed") return { Icon: CheckCircle2, color: "text-primary" };
    return { Icon: ShieldAlert, color: "text-yellow-400" };
}

function timeAgo(iso: string): string {
    const diffMs = Date.now() - new Date(iso).getTime();
    const mins = Math.max(0, Math.floor(diffMs / 60_000));
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
}

/**
 * Floating top navigation: wordmark, a pill nav with a sliding active
 * indicator, notifications from real audit history, a live backend status
 * dot, and a primary call to action. Polling pauses while the tab is hidden.
 */
export function Header() {
    const pathname = usePathname();
    const [isNotifOpen, setIsNotifOpen] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [audits, setAudits] = useState<RecentAudit[]>([]);
    const [readIds, setReadIds] = useState<Set<string>>(new Set());
    const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
    const notifRef = useRef<HTMLDivElement>(null);

    const unreadCount = audits.filter((a) => !readIds.has(a.id)).length;

    const poll = useCallback(async () => {
        if (document.hidden) return;
        const [online, recent] = await Promise.all([checkBackendHealth(), fetchRecentAudits()]);
        setBackendOnline(online);
        setAudits(recent);
    }, []);

    useEffect(() => {
        // Initial load runs as a callback rather than synchronously in the
        // effect body, so it doesn't trigger a cascading render on mount.
        const initial = setTimeout(() => {
            try {
                const saved = window.localStorage.getItem(READ_STORAGE_KEY);
                if (saved) setReadIds(new Set(JSON.parse(saved) as string[]));
            } catch {
                // ignore
            }
            poll();
        }, 0);
        const a = setInterval(poll, Math.min(HEALTH_POLL_MS, NOTIF_POLL_MS));
        document.addEventListener("visibilitychange", poll);
        return () => {
            clearTimeout(initial);
            clearInterval(a);
            document.removeEventListener("visibilitychange", poll);
        };
    }, [poll]);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
                setIsNotifOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    // Close the mobile menu on navigation by adjusting state during render
    // (React's recommended alternative to a setState-in-effect).
    const [menuPath, setMenuPath] = useState(pathname);
    if (menuPath !== pathname) {
        setMenuPath(pathname);
        setMobileOpen(false);
    }

    const markAllAsRead = () => {
        const ids = new Set(audits.map((a) => a.id));
        setReadIds(ids);
        try {
            window.localStorage.setItem(READ_STORAGE_KEY, JSON.stringify([...ids]));
        } catch {
            // ignore
        }
    };

    const isActive = (href: string) =>
        href === "/" ? pathname === "/" : pathname.startsWith(href);

    return (
        <header className="fixed inset-x-0 top-0 z-50 px-4 pt-4 sm:px-6">
            <div className="mx-auto flex h-14 max-w-6xl items-center justify-between rounded-full border border-border bg-background/80 pl-5 pr-2 backdrop-blur-md">
                {/* Wordmark */}
                <Link href="/" className="flex items-center gap-2.5 shrink-0">
                    <span className="relative flex h-2.5 w-2.5">
                        <span className="absolute inline-flex h-full w-full rounded-full bg-primary opacity-60 animate-ping" />
                        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
                    </span>
                    <span
                        className="text-[1.35rem] leading-none tracking-tight text-foreground"
                        style={{ fontFamily: "var(--font-instrument), Georgia, serif" }}
                    >
                        auditor<span className="text-primary">.</span>
                    </span>
                </Link>

                {/* Desktop nav */}
                <nav className="hidden items-center gap-0.5 lg:flex">
                    {navItems.map((item) => {
                        const active = isActive(item.href);
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "relative rounded-full px-3.5 py-1.5 text-[0.8rem] font-medium transition-colors duration-300",
                                    active ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                                )}
                            >
                                {active && (
                                    <motion.span
                                        layoutId="nav-pill"
                                        className="absolute inset-0 rounded-full bg-secondary border border-border"
                                        transition={{ type: "spring", stiffness: 420, damping: 36 }}
                                    />
                                )}
                                <span className="relative">{item.label}</span>
                            </Link>
                        );
                    })}
                </nav>

                {/* Right cluster */}
                <div className="flex items-center gap-2">
                    <div
                        className="hidden items-center gap-2 px-2 sm:flex"
                        title={backendOnline ? "Backend online" : backendOnline === false ? "Backend offline" : "Checking backend"}
                    >
                        <span
                            className={cn(
                                "h-1.5 w-1.5 rounded-full transition-colors duration-500",
                                backendOnline === null ? "bg-muted-foreground" : backendOnline ? "bg-primary" : "bg-red-400"
                            )}
                        />
                        <span className="eyebrow">
                            {backendOnline === null ? "checking" : backendOnline ? "online" : "offline"}
                        </span>
                    </div>

                    <div className="relative" ref={notifRef}>
                        <button
                            type="button"
                            aria-label="Notifications"
                            onClick={() => setIsNotifOpen((v) => !v)}
                            className="relative flex h-10 w-10 items-center justify-center rounded-full text-muted-foreground transition-colors duration-300 hover:bg-secondary hover:text-foreground"
                        >
                            <Bell className="h-4 w-4" />
                            {unreadCount > 0 && (
                                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-primary ring-2 ring-background" />
                            )}
                        </button>

                        {isNotifOpen && (
                            <div className="page-enter absolute right-0 top-12 z-50 w-80 overflow-hidden rounded-2xl border border-border bg-popover shadow-2xl shadow-black/60">
                                <div className="border-b border-border px-4 py-3">
                                    <h3 className="eyebrow">Recent audits</h3>
                                </div>
                                <div className="max-h-64 overflow-y-auto">
                                    {audits.length === 0 ? (
                                        <p className="px-4 py-8 text-center text-sm text-muted-foreground">No audits yet</p>
                                    ) : (
                                        audits.map((audit, index) => {
                                            const { Icon, color } = iconFor(audit.status);
                                            const isRead = readIds.has(audit.id);
                                            return (
                                                <Link
                                                    key={audit.id}
                                                    href={`/history/${audit.id}`}
                                                    onClick={() => setIsNotifOpen(false)}
                                                    className={cn(
                                                        "flex gap-3 px-4 py-3 transition-colors duration-200 hover:bg-secondary",
                                                        index !== audits.length - 1 && "border-b border-border",
                                                        isRead && "opacity-50"
                                                    )}
                                                >
                                                    <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", color)} />
                                                    <div className="min-w-0">
                                                        <p className="truncate text-sm font-medium text-foreground">{audit.repository}</p>
                                                        <p className="mt-0.5 text-xs text-muted-foreground">
                                                            {audit.status} · {audit.findings} finding(s) · {timeAgo(audit.date)}
                                                        </p>
                                                    </div>
                                                </Link>
                                            );
                                        })
                                    )}
                                </div>
                                <div className="border-t border-border px-4 py-2.5 text-center">
                                    <button
                                        type="button"
                                        onClick={markAllAsRead}
                                        className="text-xs text-primary transition-opacity hover:opacity-70"
                                    >
                                        Mark all as read
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    <Link href="/audit" className="btn-pill hidden sm:inline-flex">
                        Run audit
                        <ArrowUpRight className="h-3.5 w-3.5" />
                    </Link>

                    <button
                        type="button"
                        aria-label="Menu"
                        onClick={() => setMobileOpen((v) => !v)}
                        className="flex h-10 w-10 items-center justify-center rounded-full border border-border text-foreground lg:hidden"
                    >
                        {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
                    </button>
                </div>
            </div>

            {mobileOpen && (
                <nav className="page-enter mx-auto mt-2 flex max-w-6xl flex-col rounded-3xl border border-border bg-background/95 p-2 backdrop-blur-md lg:hidden">
                    {navItems.map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "rounded-2xl px-4 py-3 text-sm font-medium transition-colors",
                                isActive(item.href) ? "bg-secondary text-foreground" : "text-muted-foreground"
                            )}
                        >
                            {item.label}
                        </Link>
                    ))}
                </nav>
            )}
        </header>
    );
}
