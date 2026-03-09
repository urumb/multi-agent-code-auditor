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
const severityConfig: Record<Severity, { label: string; classes: string }> = {
    critical: {
        label: "Critical",
        classes: "bg-red-500/10 text-red-400 border-red-500/20",
    },
    warning: {
        label: "Warning",
        classes: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    },
    info: {
        label: "Info",
        classes: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    },
};

/**
 * Color-coded severity badge for audit findings.
 *
 * @param props - Badge configuration.
 */
export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
    const config = severityConfig[severity];

    return (
        <span
            className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
                config.classes,
                className
            )}
        >
            <span
                className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    severity === "critical" && "bg-red-400",
                    severity === "warning" && "bg-yellow-400",
                    severity === "info" && "bg-emerald-400"
                )}
            />
            {config.label}
        </span>
    );
}
