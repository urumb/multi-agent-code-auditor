"use client";

import { useEffect, useState } from "react";
import { MetricCard } from "@/components/dashboard/metric-card";
import { MetricCardSkeleton } from "@/components/dashboard/metric-card-skeleton";
import { TrendChart } from "@/components/dashboard/trend-chart";
import { RecentAudits } from "@/components/dashboard/recent-audits";
import { EmptyState } from "@/components/ui/empty-state";
import { fetchMetrics, fetchTrendData, fetchRecentAudits } from "@/lib/api";
import type { MetricData, TrendPoint, RecentAudit } from "@/types";
import { Play } from "lucide-react";
import Link from "next/link";

/**
 * Dashboard page showing audit overview metrics, vulnerability trends,
 * and recent audit history.
 */
export default function DashboardPage() {
  const [metrics, setMetrics] = useState<MetricData[] | null>(null);
  const [trendData, setTrendData] = useState<TrendPoint[]>([]);
  const [recentAudits, setRecentAudits] = useState<RecentAudit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [metricsData, trends, audits] = await Promise.all([
          fetchMetrics(),
          fetchTrendData(),
          fetchRecentAudits(),
        ]);
        setMetrics(metricsData);
        setTrendData(trends);
        setRecentAudits(audits);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">
          Dashboard
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Overview of your code audit activity and findings.
        </p>
      </div>

      {/* Metric cards */}
      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
            <MetricCardSkeleton key={i} />
          ))
          : metrics?.map((metric) => (
            <MetricCard
              key={metric.label}
              label={metric.label}
              value={metric.value}
              trend={metric.trend}
              trendDirection={metric.trendDirection}
              icon={metric.icon}
            />
          ))}
      </div>

      {/* Charts and recent audits */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {trendData.length > 0 ? (
            <TrendChart data={trendData} />
          ) : (
            <div className="glass-card rounded-xl p-5">
              <EmptyState
                title="No trend data"
                description="Run your first audit to see vulnerability trends."
                action={
                  <Link
                    href="/audit"
                    className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
                  >
                    <Play className="h-4 w-4" />
                    Run Audit
                  </Link>
                }
              />
            </div>
          )}
        </div>
        <div>
          {recentAudits.length > 0 ? (
            <RecentAudits audits={recentAudits} />
          ) : (
            <div className="glass-card rounded-xl p-5">
              <EmptyState
                title="No audits yet"
                description="Run your first scan to see results here."
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
