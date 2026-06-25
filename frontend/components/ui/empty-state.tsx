import { cn } from "@/lib/utils";
import { type LucideIcon, FileSearch } from "lucide-react";

/**
 * Props for the EmptyState component.
 */
interface EmptyStateProps {
    /** Icon to display above the message. */
    icon?: LucideIcon;
    /** Primary heading text. */
    title: string;
    /** Descriptive subtext. */
    description: string;
    /** Optional action element (e.g., a button). */
    action?: React.ReactNode;
    /** Additional CSS classes. */
    className?: string;
}

/**
 * Reusable empty state component for pages with no data.
 *
 * @param props - EmptyState configuration.
 */
export function EmptyState({
    icon: Icon = FileSearch,
    title,
    description,
    action,
    className,
}: EmptyStateProps) {
    return (
        <div
            className={cn(
                "flex flex-col items-center justify-center py-16 px-4 text-center",
                className
            )}
        >
            <div className="flex h-12 w-12 items-center justify-center rounded-md bg-secondary mb-4 border border-border">
                <Icon className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="text-sm font-semibold text-foreground mb-1">{title}</h3>
            <p className="text-sm text-muted-foreground max-w-sm mb-6 leading-relaxed">
                {description}
            </p>
            {action}
        </div>
    );
}
