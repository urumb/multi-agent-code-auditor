import type { FileAuditResult } from "@/lib/api";

/** Status pill for one audited file: error, unchanged (reused), or ready. */
export function FileStatusBadge({ file }: { file: FileAuditResult }) {
    if (file.error) {
        return (
            <span className="inline-flex items-center rounded-full bg-red-500/10 text-red-400 border border-red-500/20 px-2.5 py-0.5 text-xs font-medium">
                error
            </span>
        );
    }
    if (file.cached) {
        return (
            <span
                className="inline-flex items-center rounded-full bg-muted text-muted-foreground border border-border px-2.5 py-0.5 text-xs font-medium"
                title="This file hasn't changed since its last audit, so the previous result was reused."
            >
                unchanged
            </span>
        );
    }
    return (
        <span className="inline-flex items-center rounded-full bg-primary/10 text-primary border border-primary/20 px-2.5 py-0.5 text-xs font-medium">
            report ready
        </span>
    );
}
