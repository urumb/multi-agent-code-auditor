import { Skeleton } from "@/components/ui/skeleton";

/**
 * Skeleton loading state for a MetricCard.
 */
export function MetricCardSkeleton() {
    return (
        <div className="glass-card rounded-xl p-6 h-[142px]">
            <div className="flex items-start justify-between">
                <Skeleton className="h-12 w-12 rounded-full" />
                <Skeleton className="h-6 w-16 rounded-full" />
            </div>
            <div className="mt-5 space-y-2.5">
                <Skeleton className="h-10 w-24" />
                <Skeleton className="h-4 w-32" />
            </div>
        </div>
    );
}
