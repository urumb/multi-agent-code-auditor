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
        <div className="glass-card p-6">
            <h3 className="eyebrow mb-5">Findings · last 14 days</h3>
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
                                <stop offset="5%" stopColor="#3bef8c" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#3bef8c" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="#212126"
                            vertical={false}
                        />
                        <XAxis
                            dataKey="date"
                            stroke="#6d6d75"
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis
                            stroke="#6d6d75"
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: "#101013",
                                border: "1px solid #212126",
                                borderRadius: "12px",
                                color: "#f1eee6",
                                fontSize: "12px",
                            }}
                        />
                        <Legend
                            iconType="circle"
                            iconSize={8}
                            wrapperStyle={{ fontSize: "12px", color: "#8a8a92" }}
                        />
                        <Area
                            type="monotone"
                            dataKey="critical"
                            name="Critical"
                            stroke="#ef4444"
                            fill="url(#criticalGrad)"
                            strokeWidth={1.75}
                            isAnimationActive={false}
                        />
                        <Area
                            type="monotone"
                            dataKey="warning"
                            name="Warning"
                            stroke="#eab308"
                            fill="url(#warningGrad)"
                            strokeWidth={1.75}
                            isAnimationActive={false}
                        />
                        <Area
                            type="monotone"
                            dataKey="info"
                            name="Info"
                            stroke="#3bef8c"
                            fill="url(#infoGrad)"
                            strokeWidth={1.75}
                            isAnimationActive={false}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
