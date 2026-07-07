"use client";

import React, { useState, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { ViewKey, KarmaData, Task } from "@/lib/types";

interface DashboardViewProps {
  tasks: Task[];
  karmaData: KarmaData | null;
  onViewChange: (v: ViewKey) => void;
}

export default function DashboardView({
  tasks,
  karmaData,
  onViewChange,
}: DashboardViewProps) {
  const [isMounted, setIsMounted] = useState(false);
  const [coachInsight, setCoachInsight] = useState<string>("");

  useEffect(() => {
    if (karmaData) {
      const insight = generateCoachInsight(karmaData, tasks);
      setCoachInsight(insight);
    }
    // Set mounted after initial render to avoid SSR mismatch
    setIsMounted(true);
  }, [karmaData, tasks]);

  const overview = karmaData?.overview;
  const weeklyData = karmaData?.weekly_trends || [];
  const activeTasks = tasks.filter((t) => !t.completed).length;
  const highPriorityTasks = tasks.filter((t) => t.priority === "high" && !t.completed);

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Greeting Header */}
        <div className="flex items-center justify-between animate-fade-in">
          <div>
            <h2 className="text-2xl font-semibold text-white tracking-tight">
              Welcome back
            </h2>
            <p className="text-sm text-zinc-500 mt-0.5">
              {new Date().toLocaleDateString("en-US", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>
          </div>
          <img
            src="/logo.jpg"
            alt="ChitraGupta"
            className="w-12 h-12 rounded-xl object-cover ring-1 ring-zinc-800 hidden sm:block"
          />
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          <StatCard
            label="Total Karma"
            value={overview?.total_karma ?? 0}
            icon="✦"
            color="text-orange-400"
          />
          <StatCard
            label="Current Streak"
            value={`${overview?.current_streak_days ?? 0}d`}
            icon="🔥"
            color="text-yellow-400"
          />
          <StatCard
            label="Active Tasks"
            value={activeTasks}
            icon="✓"
            color="text-blue-400"
          />
          <StatCard
            label="Completion Rate"
            value={`${overview?.completion_rate ?? 0}%`}
            icon="◉"
            color="text-green-400"
          />
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Weekly Karma Chart */}
          <div className="card lg:col-span-2 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-zinc-300">Weekly Karma Trend</h3>
              <button
                onClick={() => onViewChange("karma")}
                className="text-[11px] text-zinc-500 hover:text-orange-400 transition-smooth"
              >
                View All →
              </button>
            </div>
            <div className="h-48">
              {isMounted && weeklyData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={weeklyData}>
                    <defs>
                      <linearGradient id="karmaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#f97316" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#f97316" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                    <XAxis dataKey="week_start" stroke="#444" tick={{ fontSize: 10 }} />
                    <YAxis stroke="#444" tick={{ fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{
                        background: "#111113",
                        border: "1px solid #27272a",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      labelStyle={{ color: "#71717a" }}
                      itemStyle={{ color: "#a1a1aa" }}
                    />
                    <Area
                      type="monotone"
                      dataKey="karma"
                      stroke="#f97316"
                      strokeWidth={2}
                      fill="url(#karmaGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <EmptyChart />
              )}
            </div>
          </div>

          {/* Coach Insight */}
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-3">
              <img src="/logo.jpg" alt="" className="w-6 h-6 rounded-md object-cover" />
              <h3 className="text-sm font-medium text-zinc-300">Coach Insight</h3>
            </div>
            {coachInsight ? (
              <p className="text-[13px] text-zinc-400 leading-relaxed">
                {coachInsight}
              </p>
            ) : (
              <div className="space-y-2">
                <div className="skeleton h-3 rounded" />
                <div className="skeleton h-3 rounded w-5/6" />
                <div className="skeleton h-3 rounded w-4/6" />
              </div>
            )}
          </div>

          {/* Current Focus / High Priority Tasks */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-zinc-300">Current Focus</h3>
              <button
                onClick={() => onViewChange("tasks")}
                className="text-[11px] text-zinc-500 hover:text-orange-400 transition-smooth"
              >
                View All →
              </button>
            </div>
            {highPriorityTasks.length > 0 ? (
              <div className="space-y-2">
                {highPriorityTasks.slice(0, 4).map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center gap-2.5 p-2.5 rounded-lg bg-zinc-900/50 border border-zinc-800 hover:border-zinc-700 transition-smooth"
                  >
                    <div className="w-1 h-8 rounded-full bg-red-500" />
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] text-zinc-300 truncate">{task.title}</p>
                      <p className="text-[11px] text-zinc-600 capitalize">{task.discipline}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state py-8">
                <p className="text-sm text-zinc-600">No high priority tasks</p>
                <button
                  onClick={() => onViewChange("chat")}
                  className="text-[12px] text-orange-400 hover:text-orange-300 mt-2 transition-smooth"
                >
                  Ask Coach →
                </button>
              </div>
            )}
          </div>

          {/* Behavior Insights */}
          <div className="card lg:col-span-2 p-5">
            <h3 className="text-sm font-medium text-zinc-300 mb-4">Behavior Insights</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <InsightCard
                label="Tasks Completed"
                value={overview?.total_tasks_completed ?? 0}
                total={overview?.total_tasks_attempted ?? 0}
              />
              <InsightCard
                label="Days Tracked"
                value={overview?.days_tracked ?? 0}
              />
              <InsightCard
                label="Longest Streak"
                value={`${overview?.longest_streak_days ?? 0}d`}
              />
            </div>
            <div className="mt-4 pt-4 border-t border-zinc-800">
              <p className="text-[12px] text-zinc-500">
                {overview?.days_tracked && overview.days_tracked > 0
                  ? `You've been consistent for ${overview.days_tracked} days. ${
                      overview.current_streak_days > 0
                        ? `Currently on a ${overview.current_streak_days}-day streak.`
                        : "Start a new streak today."
                    }`
                  : "Start tracking your progress today."}
              </p>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <QuickAction
            label="New Chat"
            onClick={() => onViewChange("chat")}
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            }
          />
          <QuickAction
            label="View Tasks"
            onClick={() => onViewChange("tasks")}
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
            }
          />
          <QuickAction
            label="Karma Analytics"
            onClick={() => onViewChange("karma")}
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" />
              </svg>
            }
          />
          <QuickAction
            label="Daily Review"
            onClick={() => onViewChange("review")}
            icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            }
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: string | number; icon: string; color: string }) {
  return (
    <div className="card p-4 animate-fade-in">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] text-zinc-500 uppercase tracking-wider">{label}</span>
        <span className={`text-lg ${color}`}>{icon}</span>
      </div>
      <p className="text-2xl font-semibold text-white tabular-nums">{value}</p>
    </div>
  );
}

function InsightCard({ label, value, total }: { label: string; value: string | number; total?: string | number }) {
  return (
    <div className="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800">
      <p className="text-[11px] text-zinc-500 mb-1">{label}</p>
      <p className="text-lg font-semibold text-white tabular-nums">
        {value}
        {total !== undefined && <span className="text-sm text-zinc-600"> / {total}</span>}
      </p>
    </div>
  );
}

function QuickAction({ label, onClick, icon }: { label: string; onClick: () => void; icon: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className="card p-4 flex items-center gap-3 hover:border-orange-500/30 transition-smooth text-left group"
    >
      <span className="text-zinc-500 group-hover:text-orange-400 transition-smooth">{icon}</span>
      <span className="text-[13px] text-zinc-400 group-hover:text-white transition-smooth">{label}</span>
    </button>
  );
}

function EmptyChart() {
  return (
    <div className="h-full flex items-center justify-center text-zinc-600 text-sm">
      <div className="text-center">
        <img src="/logo.jpg" alt="" className="w-10 h-10 rounded-lg object-cover mx-auto mb-2 opacity-50" />
        <p>No data yet</p>
      </div>
    </div>
  );
}

function generateCoachInsight(karma: KarmaData, tasks: Task[]): string {
  const ov = karma.overview;
  const active = tasks.filter((t) => !t.completed).length;
  
  if (ov.days_tracked === 0) {
    return "Welcome! I'm your AI coach. Start by telling me about your goals, and I'll help you build a personalized growth plan. Let's begin with a conversation.";
  }
  
  let insight = "";
  if (ov.current_streak_days >= 7) {
    insight = `Excellent work! You're on a ${ov.current_streak_days}-day streak. This momentum is powerful — `;
  } else if (ov.current_streak_days >= 3) {
    insight = `You're building momentum with a ${ov.current_streak_days}-day streak. `;
  } else {
    insight = "Let's rebuild your consistency. ";
  }
  
  if (ov.completion_rate > 80) {
    insight += `Your ${ov.completion_rate}% completion rate shows strong follow-through. `;
  } else if (ov.completion_rate > 50) {
    insight += `Your completion rate is ${ov.completion_rate}% — room to grow. `;
  }
  
  if (active > 0) {
    insight += `You have ${active} active ${active === 1 ? "task" : "tasks"} to focus on today. Priority on high-impact items will move the needle.`;
  } else {
    insight += "You have a clear slate. Consider asking me about next steps for your goals.";
  }
  
  return insight;
}