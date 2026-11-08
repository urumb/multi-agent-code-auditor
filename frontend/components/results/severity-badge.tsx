import { cn } from "@/lib/utils";
import type { Severity } from "@/types";

/**
 * Props for the SeverityBadge component.
 */
interface SeverityBadgeProps {
    /** Severity level to display. */
    severity: Severity;
    /** Additional CSS classes. */
    className?: string;
}

/** Color and label mapping for severity levels. */
const severityConfig: Record<Severity, { label: string; classes: string; dotColor: string }> = {
    critical: {
        label: "Critical",
        classes: "bg-red-500/10 text-red-400 border-red-500/20",
        dotColor: "bg-red-400",
    },
    high: {
        label: "High",
        classes: "bg-orange-500/10 text-orange-400 border-orange-500/20",
        dotColor: "bg-orange-400",
    },
    medium: {
        label: "Medium",
        classes: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
        dotColor: "bg-yellow-400",
    },
    low: {
        label: "Low",
        classes: "bg-primary/10 text-primary border-primary/20",
        dotColor: "bg-primary",
    },
};

/**
 * Color-coded severity badge for audit findings.
 *
 * @param props - Badge configuration.
 */
export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
    const config = severityConfig[severity] ?? severityConfig.low;

    return (
        <span
            className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
                config.classes,
                className
            )}
        >
            <span className={cn("h-1.5 w-1.5 rounded-full", config.dotColor)} />
            {config.label}
        </span>
    );
}
