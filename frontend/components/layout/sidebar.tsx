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
        <aside className="sticky top-0 left-0 z-40 flex h-screen w-64 flex-col bg-sidebar border-r border-border shrink-0">
            {/* Logo */}
            <div className="flex h-16 items-center gap-3 border-b border-border px-6">
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 border border-primary/20">
                    <Shield className="h-4 w-4 text-primary" />
                </div>
                <div className="flex flex-col">
                    <span className="text-sm font-bold text-foreground tracking-tight">
                        Code Auditor
                    </span>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1 px-4 py-6">
                {navItems.map((item) => {
                    const isActive =
                        pathname === item.href ||
                        (item.href !== "/" && pathname.startsWith(item.href));

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all duration-200",
                                isActive
                                    ? "bg-secondary text-foreground shadow-sm"
                                    : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                            )}
                        >
                            <item.icon className={cn("h-4 w-4", isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} />
                            {item.label}
                        </Link>
                    );
                })}
            </nav>
        </aside>
    );
}
