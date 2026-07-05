"use client";

import React, { useState, useEffect, useCallback } from "react";
import { API_BASE } from "@/lib/types";

export default function ReviewView() {
  const [tasks, setTasks] = useState([]);
  const [karmaSummary, setKarmaSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [reviewCompleted, setReviewCompleted] = useState(false);
  const [reflection, setReflection] = useState("");

  const fetchReview = useCallback(async () => {
    setLoading(true);
    try {
      const [tasksRes, karmaRes] = await Promise.all([
        fetch(`${API_BASE}/api/tasks`),
        fetch(`${API_BASE}/api/karma-summary`),
      ]);
      if (tasksRes.ok) {
        const data = await tasksRes.json();
        setTasks(data.data || data || []);
      }
      if (karmaRes.ok) {
        setKarmaSummary(await karmaRes.json());
      }
    } catch {
      // Silent fail
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchReview();
  }, [fetchReview]);

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const completedTasks = tasks.filter((t: any) => t.completed);
  const missedTasks = tasks.filter((t: any) => !t.completed);

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-4 sm:p-6 lg:p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center gap-3">
          <img src="/logo.jpg" alt="ChitraGupta" className="w-10 h-10 rounded-xl object-cover ring-1 ring-zinc-700" />
          <div>
            <h2 className="text-xl font-semibold text-white tracking-tight">Daily Review</h2>
            <p className="text-sm text-zinc-500">{today}</p>
          </div>
        </div>

        {reviewCompleted ? (
          <div className="card p-8 empty-state animate-fade-in">
            <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mb-4">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-white mb-2">Review Complete!</h3>
            <p className="text-sm text-zinc-500 max-w-md">
              You've completed your daily review. Your coach is synthesizing insights for tomorrow.
            </p>
            <button onClick={() => setReviewCompleted(false)} className="btn-ghost mt-4 px-4 py-2 text-[13px]">
              Edit Review
            </button>
          </div>
        ) : (
          <>
            <div className="card p-5">
              <h3 className="text-sm font-medium text-zinc-300 mb-3">Reflection</h3>
              <textarea
                value={reflection}
                onChange={(e) => setReflection(e.target.value)}
                placeholder="What went well today? What could be better?"
                className="w-full bg-zinc-900/60 border border-zinc-800 rounded-lg px-3 py-2.5 text-[13px] text-zinc-300 placeholder-zinc-600 focus:border-zinc-700 transition-smooth min-h-24 resize-none"
              />
            </div>

            {completedTasks.length > 0 && (
              <div className="card p-5">
                <h3 className="text-sm font-medium text-green-400 mb-3">
                  ✓ Completed Tasks ({completedTasks.length})
                </h3>
                <div className="space-y-1.5">
                  {completedTasks.map((t: any, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-[12px] text-zinc-400">
                      <span className="text-green-500">✓</span>
                      <span className="line-through text-zinc-600">{t.title}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {missedTasks.length > 0 && (
              <div className="card p-5">
                <h3 className="text-sm font-medium text-red-400 mb-3">
                  ○ Tasks Remaining ({missedTasks.length})
                </h3>
                <div className="space-y-1.5">
                  {missedTasks.map((t: any, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-[12px] text-zinc-400">
                      <span className="text-red-500">○</span>
                      <span>{t.title}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {karmaSummary && (
              <div className="card p-5 border-l-4 border-l-orange-500">
                <div className="flex items-center gap-2 mb-3">
                  <img src="/logo.jpg" alt="" className="w-6 h-6 rounded-md object-cover" />
                  <h3 className="text-sm font-medium text-zinc-300">Coach Insights</h3>
                </div>
                <p className="text-[13px] text-zinc-400 leading-relaxed">
                  Your karma is trending based on today's activity. Keep up the consistency.
                </p>
              </div>
            )}

            <button
              onClick={() => setReviewCompleted(true)}
              className="btn-primary w-full py-3 text-[14px] font-medium"
            >
              Complete Daily Review
            </button>
          </>
        )}
      </div>
    </div>
  );
}