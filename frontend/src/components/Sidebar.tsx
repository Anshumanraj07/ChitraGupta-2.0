"use client";

import React from "react";
import { type ViewKey, type KarmaData, API_BASE } from "@/lib/types";

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  activeView: ViewKey;
  onViewChange: (v: ViewKey) => void;
  karmaData: KarmaData | null;
  taskCount: number;
}

// Icon set - lightweight inline SVG
const Icons = {
  dashboard: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" />
    </svg>
  ),
  chat: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  tasks: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
    </svg>
  ),
  karma: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" />
    </svg>
  ),
  memory: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a10 10 0 1 0 10 10" /><path d="M12 6v6l4 2" /><line x1="12" y1="2" x2="22" y2="2" />
    </svg>
  ),
  review: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" /><line x1="9" y1="15" x2="15" y2="15" />
    </svg>
  ),
  settings: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  ),
  menu: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  ),
};

const navItems: { key: ViewKey; label: string; icon: React.ReactNode }[] = [
  { key: "dashboard", label: "Dashboard", icon: Icons.dashboard },
  { key: "chat", label: "Chat", icon: Icons.chat },
  { key: "tasks", label: "Tasks", icon: Icons.tasks },
  { key: "karma", label: "Karma", icon: Icons.karma },
  { key: "memory", label: "Memory", icon: Icons.memory },
  { key: "review", label: "Daily Review", icon: Icons.review },
  { key: "settings", label: "Settings", icon: Icons.settings },
];

export default function Sidebar({
  isOpen,
  onToggle,
  activeView,
  onViewChange,
  karmaData,
  taskCount,
}: SidebarProps) {
  return (
    <aside
      className={`${
        isOpen ? "w-60" : "w-16"
      } flex flex-col border-r border-zinc-800 bg-[#0d0d0d] transition-all duration-300 ease-in-out shrink-0 h-full`}
    >
      {/* Logo + Brand */}
      <div className="flex items-center h-14 border-b border-zinc-800 px-3 gap-2.5">
        <button
          onClick={onToggle}
          className="text-zinc-500 hover:text-white transition-smooth shrink-0"
          aria-label="Toggle sidebar"
        >
          {Icons.menu}
        </button>
        {isOpen && (
          <div className="flex items-center gap-2.5 animate-fade-in">
            <img
              src="/logo.jpg"
              alt="ChitraGupta Logo"
              className="w-7 h-7 rounded-lg object-cover ring-1 ring-zinc-700"
            />
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-white tracking-tight leading-none">
                ChitraGupta
              </span>
              <span className="text-[10px] text-zinc-500 tracking-wider">2.0</span>
            </div>
          </div>
        )}
        {!isOpen && (
          <img
            src="/logo.jpg"
            alt="ChitraGupta Logo"
            className="w-8 h-8 rounded-lg object-cover ring-1 ring-zinc-700 mx-auto"
          />
        )}
      </div>

      {/* Nav items */}
      <nav className="flex-1 py-3 space-y-0.5 px-2 overflow-y-auto scrollbar-thin">
        {navItems.map((item) => (
          <button
            key={item.key}
            onClick={() => onViewChange(item.key)}
            className={`flex items-center gap-3 w-full px-2.5 py-2 rounded-lg transition-smooth text-[13px] ${
              activeView === item.key
                ? "bg-zinc-800/80 text-white"
                : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/50"
            }`}
            title={item.label}
          >
            <span className="shrink-0">{item.icon}</span>
            {isOpen && <span className="truncate">{item.label}</span>}
            {isOpen && item.key === "tasks" && taskCount > 0 && (
              <span className="ml-auto text-[10px] bg-zinc-700 px-1.5 py-0.5 rounded-full text-zinc-300">
                {taskCount}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* Karma mini stats */}
      {isOpen && karmaData && (
        <div className="border-t border-zinc-800 px-3 py-3 space-y-2 animate-fade-in">
          <p className="text-[10px] tracking-widest uppercase text-zinc-600 mb-1">
            Karma Overview
          </p>
          <MiniStat label="Total Karma" value={karmaData.overview.total_karma} />
          <MiniStat
            label="Streak"
            value={karmaData.overview.current_streak_days}
            suffix="d"
          />
          <MiniStat
            label="Completion"
            value={karmaData.overview.completion_rate}
            suffix="%"
          />
          <MiniStat
            label="Tasks Done"
            value={karmaData.overview.total_tasks_completed}
          />
        </div>
      )}

      {/* Footer */}
      {isOpen && (
        <div className="border-t border-zinc-800 px-3 py-2.5">
          <div className="flex items-center gap-2 text-[11px] text-zinc-600">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500/70" />
            <span>System Online</span>
          </div>
        </div>
      )}
    </aside>
  );
}

function MiniStat({
  label,
  value,
  suffix = "",
}: {
  label: string;
  value: number;
  suffix?: string;
}) {
  return (
    <div className="flex items-center justify-between text-[11px]">
      <span className="text-zinc-600">{label}</span>
      <span className="text-zinc-400 tabular-nums font-medium">
        {value}
        {suffix}
      </span>
    </div>
  );
}