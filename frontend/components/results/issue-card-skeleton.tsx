import { Skeleton } from "@/components/ui/skeleton";

/**
 * Skeleton loading state for an IssueCard.
 */
export function IssueCardSkeleton() {
    return (
        <div className="glass-card rounded-xl p-4 space-y-3">
            <div className="flex items-center gap-2">
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-4 w-24" />
            </div>
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-12 w-full rounded-lg" />
        </div>
    );
}
