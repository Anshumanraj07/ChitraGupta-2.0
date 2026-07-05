"use client";

import React, { useState, useEffect, useCallback } from "react";
import { API_BASE } from "@/lib/types";

interface MemoryViewProps {
  searchQuery: string;
}

interface Memory {
  id: string;
  content: string;
  type: string;
  date: string;
  metadata?: Record<string, any>;
}

export default function MemoryView({ searchQuery }: MemoryViewProps) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [dailySummaries, setDailySummaries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState("all");

  const fetchBudget = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/daily-summaries?days=30`);
      if (res.ok) {
        const data = await res.json();
        setDailySummaries(data.summaries || []);
      }
    } catch {
      // Silent fail
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchBudget();
  }, [fetchBudget]);

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white tracking-tight">Memory Timeline</h2>
            <p className="text-sm text-zinc-500 mt-0.5">Your behavioral patterns and stored memories</p>
          </div>
        </div>

        {/* Daily Summaries */}
        {dailySummaries.length > 0 && (
          <div className="card p-5">
            <h3 className="text-sm font-medium text-zinc-300 mb-4">Recent Daily Summaries</h3>
            <div className="space-y-2">
              {dailySummaries.slice(0, 10).map((summary: any, i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 transition-smooth"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[12px] text-zinc-400">{summary.date}</span>
                    <span className="text-[11px] text-orange-400">Karma: {summary.karma || 0}</span>
                  </div>
                  <p className="text-[12px] text-zinc-500">
                    {summary.summary || "No summary available"}
                  </p>
                  {summary.goals_addressed && summary.goals_addressed.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {summary.goals_addressed.map((goal: string, j: number) => (
                        <span key={j} className="text-[10px] bg-zinc-800 px-2 py-0.5 rounded text-zinc-400">
                          {goal}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {dailySummaries.length === 0 && !loading && (
          <div className="card empty-state">
            <img src="/logo.jpg" alt="" className="w-14 h-14 rounded-xl object-cover mb-3 opacity-40" />
            <p className="text-sm text-zinc-600">No memories yet</p>
            <p className="text-[11px] text-zinc-700 mt-1">
              Start chatting with the coach to build your memory timeline
            </p>
          </div>
        )}

        {loading && (
          <div className="card p-5 space-y-3">
            <div className="skeleton h-4 rounded w-1/3" />
            <div className="skeleton h-3 rounded" />
            <div className="skeleton h-3 rounded w-5/6" />
            <div className="skeleton h-3 rounded w-4/6" />
          </div>
        )}

        {/* Behavior Evolution */}
        <div className="card p-5">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">Behavior Evolution</h3>
          <p className="text-[12px] text-zinc-500 leading-relaxed">
            Behavioral patterns are inferred from your interactions and task completion data.
            As you continue using ChitraGupta, your behavioral trends will become clearer.
          </p>
        </div>

        {/* Goal Evolution */}
        <div className="card p-5">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">Goal Evolution</h3>
          <p className="text-[12px] text-zinc-500 leading-relaxed">
            Your goal areas evolve as the coach learns more about your aspirations and priorities.
          </p>
        </div>
      </div>
    </div>
  );
}