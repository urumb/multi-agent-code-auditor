"use client";

import { useEffect, useState } from "react";
import { MetricCard } from "@/components/dashboard/metric-card";
import { MetricCardSkeleton } from "@/components/dashboard/metric-card-skeleton";
import dynamic from "next/dynamic";
import { RecentAudits } from "@/components/dashboard/recent-audits";
import { EmptyState } from "@/components/ui/empty-state";
import { fetchMetrics, fetchTrendData, fetchRecentAudits } from "@/lib/api";
import type { MetricData, TrendPoint, RecentAudit } from "@/types";
import { Play } from "lucide-react";

// Recharts is heavy; load it only when the dashboard actually has data to plot.
const TrendChart = dynamic(
  () => import("@/components/dashboard/trend-chart").then((m) => m.TrendChart),
  { ssr: false, loading: () => <div className="glass-card h-[22rem] animate-pulse" /> }
);
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
    let mounted = true;

    async function loadData() {
      // Skip refreshes while the tab isn't visible — no point polling the
      // backend for a dashboard nobody's looking at.
      if (document.hidden) return;
      try {
        const [metricsData, trends, audits] = await Promise.all([
          fetchMetrics(),
          fetchTrendData(),
          fetchRecentAudits(),
        ]);
        if (mounted) {
          setMetrics(metricsData);
          setTrendData(trends);
          setRecentAudits(audits);
          setLoading(false);
        }
      } catch {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadData();
    const interval = setInterval(loadData, 15000);
    document.addEventListener("visibilitychange", loadData);

    return () => {
      mounted = false;
      clearInterval(interval);
      document.removeEventListener("visibilitychange", loadData);
    };
  }, []);

  const isInitialLoad = loading && !metrics && trendData.length === 0 && recentAudits.length === 0;

  return (
    <div className="space-y-10">
      {/* Page header */}
      <div className="pt-4">
        <p className="eyebrow mb-4">Multi-agent code audit</p>
        <h1>
          Four agents.<br />
          <span className="text-muted-foreground">One honest review.</span>
        </h1>
        <p className="max-w-xl">
          Security, performance and quality agents inspect your code, then a
          reviewer merges their findings into a single report. Runs fully local.
        </p>
        <Link href="/audit" className="btn-pill mt-7">
          Start an audit
          <Play className="h-3.5 w-3.5" />
        </Link>
      </div>

      {/* Metric cards */}
      <div className="stagger grid gap-4 md:grid-cols-3">
        {isInitialLoad
          ? Array.from({ length: 3 }).map((_, i) => (
            <MetricCardSkeleton key={i} />
          ))
          : metrics?.map((metric, i) => (
            <MetricCard
              key={metric.label}
              index={i}
              label={metric.label}
              value={metric.value}
              trend={metric.trend}
              trendDirection={metric.trendDirection}
              icon={metric.icon}
            />
          ))}
      </div>

      {/* Charts and recent audits */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {trendData.length > 0 ? (
            <TrendChart data={trendData} />
          ) : (
            <div className="glass-card p-5">
              <EmptyState
                title="No trend data"
                description="Run your first audit to see vulnerability trends."
                action={
                  <Link
                    href="/audit"
                    className="btn-pill"
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
            <div className="glass-card p-5">
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
