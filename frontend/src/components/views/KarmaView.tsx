"use client";

import React, { useState, useMemo, useEffect } from "react";
import { BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { KarmaData } from "@/lib/types";

interface KarmaViewProps {
  karmaData: KarmaData | null;
}

export default function KarmaView({ karmaData }: KarmaViewProps) {
  const [isMounted, setIsMounted] = useState(false);
  const [timeRange, setTimeRange] = useState<"weekly" | "monthly">("weekly");

  React.useEffect(() => setIsMounted(true), []);

  const overview = karmaData?.overview;
  const weeklyData = karmaData?.weekly_trends || [];
  const monthlyData = karmaData?.monthly_trends || [];
  const heatmap = karmaData?.completion_heatmap || {};
  const goalAreas = karmaData?.goal_areas || {};

  const heatmapData = useMemo(() => {
    const entries = Object.entries(heatmap).sort((a, b) => a[0].localeCompare(b[0]));
    return entries.slice(-365); // Last 365 days
  }, [heatmap]);

  const chartData = timeRange === "weekly" ? weeklyData : monthlyData;
  const xAxisKey = timeRange === "weekly" ? "week_start" : "month";

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-4 sm:p-6 lg:p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Heatmap */}
        <div className="card p-5 overflow-x-auto">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">Completion Heatmap</h3>
          <div className="grid grid-flow-col gap-1" style={{ gridTemplateRows: "repeat(7, minmax(0, 1fr))" }}>
            {heatmapData.length > 0 ? (
              heatmapData.map(([date, count]) => {
                const level = count === 0 ? 0 : count <= 2 ? 1 : count <= 5 ? 2 : count <= 8 ? 3 : 4;
                return (
                  <div
                    key={date}
                    className="heatmap-cell w-3 h-3"
                    data-level={level}
                    title={`${date}: ${count} tasks`}
                  />
                );
              })
            ) : (
              <p className="text-[12px] text-zinc-600 col-span-7">No heatmap data</p>
            )}
          </div>
          <div className="flex items-center gap-2 mt-3 text-[10px] text-zinc-600">
            <span>Less</span>
            <div className="heatmap-cell w-3 h-3" data-level="0" />
            <div className="heatmap-cell w-3 h-3" data-level="1" />
            <div className="heatmap-cell w-3 h-3" data-level="2" />
            <div className="heatmap-cell w-3 h-3" data-level="3" />
            <div className="heatmap-cell w-3 h-3" data-level="4" />
            <span>More</span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Total Karma" value={overview?.total_karma ?? 0} color="text-orange-400" />
          <StatCard label="Avg Daily Karma" value={overview?.average_daily_karma ?? 0} />
          <StatCard label="Current Streak" value={`${overview?.current_streak_days ?? 0}d`} color="text-yellow-400" />
          <StatCard label="Longest Streak" value={`${overview?.longest_streak_days ?? 0}d`} color="text-green-400" />
          <StatCard label="Tasks Completed" value={overview?.total_tasks_completed ?? 0} color="text-blue-400" />
          <StatCard label="Tasks Attempted" value={overview?.total_tasks_attempted ?? 0} />
          <StatCard label="Completion Rate" value={`${overview?.completion_rate ?? 0}%`}/>
          <StatCard label="Days Tracked" value={overview?.days_tracked ?? 0} />
        </div>

        {/* Time Range Toggle */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-0.5 bg-zinc-900/60 rounded-lg p-0.5 border border-zinc-800">
            <button
              onClick={() => setTimeRange("weekly")}
              className={`px-3 py-1.5 rounded-md text-[12px] transition-smooth ${
                timeRange === "weekly" ? "bg-zinc-800 text-white" : "text-zinc-500"
              }`}
            >
              Weekly
            </button>
            <button
              onClick={() => setTimeRange("monthly")}
              className={`px-3 py-1.5 rounded-md text-[12px] transition-smooth ${
                timeRange === "monthly" ? "bg-zinc-800 text-white" : "text-zinc-500"
              }`}
            >
              Monthly
            </button>
          </div>
        </div>

        {/* Karma Trend Chart */}
        <div className="card p-5">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">Karma Trend</h3>
          <div className="h-64">
            {isMounted && chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData as any}>
                  <defs>
                    <linearGradient id="karmaG" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#f97316" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#f97316" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                  <XAxis dataKey={xAxisKey} stroke="#444" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#444" tick={{ fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ background: "#111113", border: "1px solid #27272a", borderRadius: "8px", fontSize: "12px" }}
                    labelStyle={{ color: "#71717a" }}
                    itemStyle={{ color: "#a1a1aa" }}
                  />
                  <Area type="monotone" dataKey="karma" stroke="#f97316" strokeWidth={2} fill="url(#karmaG)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center">
                <p className="text-sm text-zinc-600">No trend data available</p>
              </div>
            )}
          </div>
        </div>

        {/* Completion Chart */}
        <div className="card p-5">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">Task Completion</h3>
          <div className="h-48">
            {isMounted && chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData as any}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                  <XAxis dataKey={xAxisKey} stroke="#444" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#444" tick={{ fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ background: "#111113", border: "1px solid #27272a", borderRadius: "8px", fontSize: "12px" }}
                    labelStyle={{ color: "#71717a" }}
                    itemStyle={{ color: "#a1a1aa" }}
                  />
                  <Bar dataKey="completed" fill="#22c55e" radius={[4, 4, 0, 0]} name="Completed" />
                  <Bar dataKey="attempted" fill="#3f3f46" radius={[4, 4, 0, 0]} name="Attempted" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-zinc-600">No data</p>
            )}
          </div>
        </div>

        {/* Goal Areas */}
        {Object.keys(goalAreas).length > 0 && (
          <div className="card p-5">
            <h3 className="text-sm font-medium text-zinc-300 mb-4">Goal Areas</h3>
            <div className="space-y-2">
              {Object.entries(goalAreas).map(([area, count]) => (
                <div key={area} className="flex items-center gap-3">
                  <span className="text-[12px] text-zinc-400 w-32 truncate">{area}</span>
                  <div className="flex-1 bg-zinc-800 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full bg-orange-500 rounded-full transition-all"
                      style={{ width: `${Math.min((count / Math.max(...Object.values(goalAreas))) * 100, 100)}%` }}
                    />
                  </div>
                  <span className="text-[11px] text-zinc-600 tabular-nums">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, color = "text-white" }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="card p-4 animate-fade-in">
      <p className="text-[11px] text-zinc-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-semibold tabular-nums ${color}`}>{value}</p>
    </div>
  );
}