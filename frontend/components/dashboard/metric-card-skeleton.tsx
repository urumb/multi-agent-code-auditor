import { Skeleton } from "@/components/ui/skeleton";

/**
 * Skeleton loading state for a MetricCard.
 */
export function MetricCardSkeleton() {
    return (
        <div className="glass-card p-6 h-[142px]">
            <div className="flex items-start justify-between">
                <Skeleton className="h-10 w-10 rounded-md" />
                <Skeleton className="h-5 w-16 rounded-full" />
            </div>
            <div className="mt-6 space-y-2">
                <Skeleton className="h-9 w-20" />
                <Skeleton className="h-4 w-28" />
            </div>
        </div>
    );
}
