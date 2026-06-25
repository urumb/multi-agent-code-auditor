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
        classes: "bg-destructive/10 text-destructive border-destructive/20",
    },
    warning: {
        label: "Warning",
        classes: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    },
    info: {
        label: "Info",
        classes: "bg-primary/10 text-primary border-primary/20",
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
                "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider",
                config.classes,
                className
            )}
        >
            <span
                className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    severity === "critical" && "bg-destructive",
                    severity === "warning" && "bg-amber-500",
                    severity === "info" && "bg-primary"
                )}
            />
            {config.label}
        </span>
    );
}
