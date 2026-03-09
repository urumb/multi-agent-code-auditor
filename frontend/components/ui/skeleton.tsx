import { cn } from "@/lib/utils";

/**
 * Generic skeleton loading placeholder.
 *
 * @param props - HTML div props including optional className.
 */
function Skeleton({
    className,
    ...props
}: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            className={cn(
                "animate-pulse rounded-md bg-slate-800",
                className
            )}
            {...props}
        />
    );
}

export { Skeleton };
