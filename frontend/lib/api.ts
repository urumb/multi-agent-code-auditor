import type { AuditInput, AuditResult, MetricData, RecentAudit, TrendPoint } from "@/types";
import {
    mockMetrics,
    mockTrendData,
    mockAuditResult,
} from "@/lib/mock-data";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Performs a fetch request against the backend API.
 *
 * @param endpoint - API endpoint path.
 * @param options - Optional fetch init configuration.
 * @returns The parsed JSON response.
 */
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });

    if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<T>;
}

/**
 * Fetches dashboard metrics, falling back to mock data.
 *
 * @returns Array of metric data points.
 */
export async function fetchMetrics(): Promise<MetricData[]> {
    try {
        return await apiFetch<MetricData[]>("/api/metrics");
    } catch {
        return mockMetrics;
    }
}

/**
 * Fetches vulnerability trend data, falling back to mock data.
 *
 * @returns Array of trend data points.
 */
export async function fetchTrendData(): Promise<TrendPoint[]> {
    try {
        return await apiFetch<TrendPoint[]>("/api/trends");
    } catch {
        return mockTrendData;
    }
}

/**
 * Fetches recent audit history, falling back to mock data.
 *
 * @returns Array of recent audit summaries.
 */
export async function fetchRecentAudits(): Promise<RecentAudit[]> {
    try {
        return await apiFetch<RecentAudit[]>("/api/audits/recent");
    } catch {
        // Return empty array when backend is unavailable — no mock data
        return [];
    }
}

/**
 * Submits an audit request to the backend, falling back to mock result.
 *
 * @param input - Audit input configuration.
 * @returns The audit result.
 */
export async function submitAudit(input: AuditInput): Promise<AuditResult> {
    try {
        return await apiFetch<AuditResult>("/api/audit", {
            method: "POST",
            body: JSON.stringify(input),
        });
    } catch {
        // Simulate delay for mock
        await new Promise((resolve) => setTimeout(resolve, 2000));
        return mockAuditResult;
    }
}

/**
 * Fetches a specific audit result by ID, falling back to mock data.
 *
 * @param id - Audit identifier.
 * @returns The audit result.
 */
export async function fetchAuditResult(id: string): Promise<AuditResult> {
    try {
        return await apiFetch<AuditResult>(`/api/audits/${id}`);
    } catch {
        return { ...mockAuditResult, id };
    }
}
