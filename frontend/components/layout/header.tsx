"use client";

import { useState, useRef, useEffect } from "react";
import { Bell, Search, ShieldAlert, CheckCircle2, Lightbulb } from "lucide-react";
import type { LucideIcon } from "lucide-react";

/** Notification item shape stored in localStorage. */
interface Notification {
    id: number;
    title: string;
    description: string;
    time: string;
    icon: string; // serialisable key into iconMap
    iconColor: string;
    read: boolean;
}

/** Notification icon map for serialisation-safe rendering. */
const iconMap: Record<string, LucideIcon> = {
    CheckCircle2,
    ShieldAlert,
    Lightbulb,
};

/** Seed notification data shown on first visit. */
const seedNotifications: Notification[] = [
    {
        id: 1,
        title: "Audit Completed",
        description: "Repository: acme/payment-service",
        time: "2m ago",
        icon: "CheckCircle2",
        iconColor: "text-emerald-400",
        read: false,
    },
    {
        id: 2,
        title: "Security Warning Detected",
        description: "Repository: acme/auth-gateway",
        time: "15m ago",
        icon: "ShieldAlert",
        iconColor: "text-red-400",
        read: false,
    },
    {
        id: 3,
        title: "New Suggestions Generated",
        description: "Review your latest audit results.",
        time: "1h ago",
        icon: "Lightbulb",
        iconColor: "text-yellow-400",
        read: false,
    },
];

/**
 * Top header component with search, notifications, and backend status.
 */
export function Header() {
    const [isNotifOpen, setIsNotifOpen] = useState(false);
    // Start with seed data (safe for SSR), then hydrate from localStorage after mount.
    const [notifs, setNotifs] = useState<Notification[]>(seedNotifications);
    const notifRef = useRef<HTMLDivElement>(null);

    const unreadCount = notifs.filter((n) => !n.read).length;

    /** Hydrate from localStorage after first client render. */
    useEffect(() => {
        try {
            const saved = localStorage.getItem("notifications");
            if (saved) {
                const parsed = JSON.parse(saved) as Notification[];
                setNotifs(parsed);
            }
        } catch {
            // ignore parse errors
        }
    }, []);

    /** Close panel when clicking outside. */
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
                setIsNotifOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    /** Persist notifications to localStorage whenever state changes. */
    useEffect(() => {
        try {
            localStorage.setItem("notifications", JSON.stringify(notifs));
        } catch {
            // silently ignore storage errors (e.g. private mode)
        }
    }, [notifs]);

    /** Mark every notification as read and clear the badge. */
    const markAllAsRead = () => {
        const updated = notifs.map((n) => ({ ...n, read: true }));
        setNotifs(updated);
        // Also write directly so badge clears before the persist effect fires.
        try {
            localStorage.setItem("notifications", JSON.stringify(updated));
        } catch {
            // ignore
        }
    };

    return (
        <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between border-b border-border bg-background/50 backdrop-blur-xl px-6 transition-all duration-200 overflow-visible">
            {/* Search */}
            <div className="relative flex-1 max-w-md group">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors duration-200" />
                <input
                    type="text"
                    placeholder="Search audits, files, findings..."
                    className="w-full rounded-lg border border-white/5 bg-white/5 py-2 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 focus:bg-white/10 transition-all duration-200"
                />
            </div>

            {/* Right section */}
            <div className="flex items-center gap-4 ml-4">
                {/* Notification Bell */}
                <div className="relative" ref={notifRef}>
                    <button
                        type="button"
                        onClick={() => setIsNotifOpen(!isNotifOpen)}
                        className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-white/5 bg-white/5 text-muted-foreground hover:text-foreground hover:bg-white/10 hover:border-white/10 hover:shadow-md transition-all duration-200 group"
                    >
                        <Bell className="h-4 w-4 group-hover:scale-110 transition-transform duration-200" />
                        {unreadCount > 0 && (
                            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-blue-500 text-[10px] font-bold text-white shadow-sm ring-2 ring-background">
                                {unreadCount}
                            </span>
                        )}
                    </button>

                    {/* Notification Dropdown Panel */}
                    {isNotifOpen && (
                        <div className="absolute right-0 top-14 z-50 w-80 rounded-xl bg-slate-900/70 backdrop-blur-xl border border-white/10 shadow-2xl">
                            {/* Glass Overlay Layer */}
                            <div className="absolute inset-0 bg-black/20 backdrop-blur-xl rounded-xl pointer-events-none" />

                            {/* Content */}
                            <div className="relative flex flex-col">
                                {/* Header */}
                                <div className="px-4 py-3 border-b border-white/10">
                                    <h3 className="text-sm font-semibold text-white/90">Notifications</h3>
                                </div>

                                {/* Scrollable list */}
                                <div className="max-h-64 overflow-y-auto">
                                    {notifs.length === 0 ? (
                                        <p className="px-4 py-6 text-sm text-center text-muted-foreground">
                                            No notifications
                                        </p>
                                    ) : (
                                        notifs.map((notif, index) => {
                                            const IconComponent = iconMap[notif.icon] ?? Bell;
                                            return (
                                                <div
                                                    key={notif.id}
                                                    className={[
                                                        "px-4 py-3 rounded-lg hover:bg-white/5 transition-colors cursor-pointer flex gap-3",
                                                        index !== notifs.length - 1 ? "border-b border-white/5" : "",
                                                        notif.read ? "opacity-50" : "",
                                                    ].join(" ")}
                                                >
                                                    <div className={`mt-0.5 shrink-0 ${notif.iconColor}`}>
                                                        <IconComponent className="h-4 w-4" />
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-medium text-foreground leading-tight mb-1">
                                                            {notif.title}
                                                        </p>
                                                        <p className="text-xs text-muted-foreground line-clamp-2">
                                                            {notif.description}
                                                        </p>
                                                        <p className="text-[10px] text-slate-500 mt-1.5 font-medium">
                                                            {notif.time}
                                                        </p>
                                                    </div>
                                                </div>
                                            );
                                        })
                                    )}
                                </div>

                                {/* Sticky Footer */}
                                <div className="px-4 py-3 border-t border-white/10 text-center">
                                    <button
                                        type="button"
                                        onClick={markAllAsRead}
                                        className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                                    >
                                        Mark all as read
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Backend Status Indicator */}
                <div className="flex items-center gap-2 text-sm text-green-400 font-medium bg-white/5 hover:bg-white/10 transition-colors border border-white/10 px-3 py-1.5 rounded-full">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                    </span>
                    Backend Online
                </div>
            </div>
        </header>
    );
}
