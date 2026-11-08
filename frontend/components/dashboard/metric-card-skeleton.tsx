import { Skeleton } from "@/components/ui/skeleton";

/**
 * Skeleton loading state for a MetricCard (matches its new layout).
 */
export function MetricCardSkeleton() {
    return (
        <div className="glass-card p-6 h-[158px]">
            <div className="flex items-start justify-between">
                <Skeleton className="h-3 w-24" />
                <Skeleton className="h-4 w-4 rounded-full" />
            </div>
            <Skeleton className="mt-9 h-14 w-20" />
        </div>
    );
}
