"use client";

import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
} from "recharts";
import type { TrendPoint } from "@/types";

/**
 * Props for the TrendChart component.
 */
interface TrendChartProps {
    /** Trend data points to visualize. */
    data: TrendPoint[];
}

/**
 * Vulnerability trend chart using stacked area visualization.
 *
 * @param props - Chart data.
 */
export function TrendChart({ data }: TrendChartProps) {
    return (
        <div className="glass-card rounded-xl p-5">
            <h3 className="text-sm font-semibold text-foreground mb-4">
                Vulnerability Trends
            </h3>
            <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                        <defs>
                            <linearGradient id="criticalGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="warningGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#eab308" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#eab308" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="infoGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="oklch(0.25 0.02 260)"
                            vertical={false}
                        />
                        <XAxis
                            dataKey="date"
                            stroke="oklch(0.5 0.02 260)"
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis
                            stroke="oklch(0.5 0.02 260)"
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: "oklch(0.18 0.02 260)",
                                border: "1px solid oklch(0.3 0.02 260)",
                                borderRadius: "8px",
                                color: "oklch(0.9 0.01 260)",
                                fontSize: "12px",
                            }}
                        />
                        <Legend
                            iconType="circle"
                            iconSize={8}
                            wrapperStyle={{ fontSize: "12px", color: "oklch(0.7 0.02 260)" }}
                        />
                        <Area
                            type="monotone"
                            dataKey="critical"
                            name="Critical"
                            stroke="#ef4444"
                            fill="url(#criticalGrad)"
                            strokeWidth={2}
                        />
                        <Area
                            type="monotone"
                            dataKey="warning"
                            name="Warning"
                            stroke="#eab308"
                            fill="url(#warningGrad)"
                            strokeWidth={2}
                        />
                        <Area
                            type="monotone"
                            dataKey="info"
                            name="Info"
                            stroke="#10b981"
                            fill="url(#infoGrad)"
                            strokeWidth={2}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
