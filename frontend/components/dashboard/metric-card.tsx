import { cn } from "@/lib/utils";
import {
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
    icon,
    className,
}: MetricCardProps) {
    const IconComponent = iconMap[icon] ?? FolderGit2;

    return (
        <div
            className={cn(
                "glass-card p-6 transition-colors duration-200 hover:border-primary/30",
                className
            )}
        >
            <div className="flex items-start justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-secondary/50 border border-border">
                    <IconComponent className="h-5 w-5 text-muted-foreground" />
                </div>
            </div>
            <div className="mt-6">
                <p className="text-3xl font-bold text-foreground tracking-tight">
                    {value.toLocaleString()}
                </p>
                <p className="mt-1 text-sm font-medium text-muted-foreground">{label}</p>
            </div>
        </div>
    );
}
