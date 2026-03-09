"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
    LayoutDashboard,
    Play,
    FileText,
    Bot,
    Settings,
    Shield,
} from "lucide-react";

/** Navigation items configuration. */
const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/audit", label: "Run Audit", icon: Play },
    { href: "/results", label: "Results", icon: FileText },
    { href: "/agents", label: "Agents", icon: Bot },
    { href: "/settings", label: "Settings", icon: Settings },
];

/**
 * Sidebar navigation component with active-page highlighting.
 */
export function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="sticky top-0 left-0 z-40 flex h-screen w-64 flex-col bg-slate-900/80 backdrop-blur-md border-r border-white/10 shrink-0">
            {/* Logo */}
            <div className="flex h-16 items-center gap-3 border-b border-white/5 px-6">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 glow-primary border border-primary/20">
                    <Shield className="h-5 w-5 text-primary" />
                </div>
                <div className="flex flex-col">
                    <span className="text-sm font-bold text-foreground tracking-tight">
                        Code Auditor
                    </span>
                    <span className="text-[10px] text-muted-foreground uppercase tracking-widest">
                        Multi-Agent
                    </span>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1.5 px-3 py-6">
                {navItems.map((item) => {
                    const isActive =
                        pathname === item.href ||
                        (item.href !== "/" && pathname.startsWith(item.href));

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 border-l-2",
                                isActive
                                    ? "bg-white/10 text-primary border-blue-400 shadow-sm"
                                    : "border-transparent text-sidebar-foreground hover:bg-white/5 hover:text-foreground hover:border-white/10"
                            )}
                        >
                            <item.icon className={cn("h-4 w-4", isActive && "text-primary")} />
                            {item.label}
                            {isActive && (
                                <div className="ml-auto flex items-center justify-center">
                                    <span className="relative flex h-2 w-2">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                                        <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                                    </span>
                                </div>
                            )}
                        </Link>
                    );
                })}
            </nav>

        </aside>
    );
}
