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
 * Dashboard metric card displaying a KPI with trend indicator.
 *
 * @param props - Metric card configuration.
 */
export function MetricCard({
    label,
    value,
    trend,
    trendDirection,
    icon,
    className,
}: MetricCardProps) {
    const IconComponent = iconMap[icon] ?? FolderGit2;
    const isPositiveTrend = trendDirection === "down" && icon === "shield-alert";
    const trendPositive =
        (trendDirection === "up" && icon !== "shield-alert" && icon !== "bug") ||
        (trendDirection === "down" && (icon === "shield-alert" || icon === "bug"));

    return (
        <div
            className={cn(
                "glass-card rounded-xl p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl group",
                className
            )}
        >
            <div className="flex items-start justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-800/80 border border-slate-700/50 group-hover:bg-primary/20 group-hover:border-primary/30 transition-all duration-300 shadow-inner">
                    <IconComponent className="h-6 w-6 text-primary group-hover:scale-110 transition-transform duration-300" />
                </div>
                <div
                    className={cn(
                        "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold shadow-sm border",
                        trendPositive
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : "bg-red-500/10 text-red-400 border-red-500/20"
                    )}
                >
                    {trendDirection === "up" ? (
                        <TrendingUp className="h-3.5 w-3.5" />
                    ) : (
                        <TrendingDown className="h-3.5 w-3.5" />
                    )}
                    {trendDirection === "up" ? "+" : "-"}{Math.abs(trend)}%
                </div>
            </div>
            <div className="mt-5">
                <p className="text-4xl font-bold text-foreground tracking-tight drop-shadow-sm">
                    {value.toLocaleString()}
                </p>
                <p className="mt-1.5 text-sm font-medium text-slate-400">{label}</p>
            </div>
        </div>
    );
}
