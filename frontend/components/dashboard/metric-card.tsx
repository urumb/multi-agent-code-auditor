import { cn } from "@/lib/utils";
import {
    TrendingUp,
    TrendingDown,
    FolderGit2,
    ShieldAlert,
    Bug,
    Gauge,
    type LucideIcon,
} from "lucide-react";

/**
 * Props for the MetricCard component.
 */
interface MetricCardProps {
    /** Display label for the metric. */
    label: string;
    /** Numeric value. */
    value: number;
    /** Trend percentage change. */
    trend: number;
    /** Trend direction. */
    trendDirection: "up" | "down";
    /** Lucide icon name string. */
    icon: string;
    /** Stagger index for entrance animation. */
    index?: number;
    /** Additional CSS classes. */
    className?: string;
}

/** Maps icon names to Lucide icon components. */
const iconMap: Record<string, LucideIcon> = {
    "folder-git-2": FolderGit2,
    "shield-alert": ShieldAlert,
    bug: Bug,
    gauge: Gauge,
};

/**
 * Dashboard metric card displaying a KPI with an optional trend indicator.
 * The trend badge only renders when there's a real nonzero trend — the
 * backend doesn't fabricate a percentage when it has no historical basis
 * for one.
 */
export function MetricCard({
    label,
    value,
    trend,
    trendDirection,
    icon,
    index = 0,
    className,
}: MetricCardProps) {
    const IconComponent = iconMap[icon] ?? FolderGit2;
    const trendPositive =
        (trendDirection === "up" && icon !== "shield-alert" && icon !== "bug") ||
        (trendDirection === "down" && (icon === "shield-alert" || icon === "bug"));

    return (
        <div
            className={cn("glass-card p-6", className)}
            style={{ "--i": index } as React.CSSProperties}
        >
            <div className="flex items-start justify-between">
                <p className="eyebrow">{label}</p>
                <IconComponent className="h-4 w-4 text-muted-foreground" />
                {trend !== 0 && (
                    <div
                        className={cn(
                            "flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold border",
                            trendPositive
                                ? "bg-primary/10 text-primary border-primary/20"
                                : "bg-red-500/10 text-red-400 border-red-500/20"
                        )}
                    >
                        {trendDirection === "up" ? (
                            <TrendingUp className="h-3 w-3" />
                        ) : (
                            <TrendingDown className="h-3 w-3" />
                        )}
                        {trendDirection === "up" ? "+" : "-"}{Math.abs(trend)}%
                    </div>
                )}
            </div>
            <div className="mt-8">
                <p
                    className="text-6xl leading-none tracking-tight text-foreground tabular-nums"
                    style={{ fontFamily: "var(--font-instrument), Georgia, serif" }}
                >
                    {value.toLocaleString()}
                </p>
            </div>
        </div>
    );
}
