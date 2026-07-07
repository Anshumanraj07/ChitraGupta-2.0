"use client";

import React, { useState } from "react";
import { useAuth } from "@/lib/auth";

interface TopBarProps {
  title: string;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onMenuClick: () => void;
}

export default function TopBar({
  title,
  searchQuery,
  onSearchChange,
  onMenuClick,
}: TopBarProps) {
  const { user, signOut } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <header className="h-14 border-b border-zinc-800 flex items-center justify-between px-4 sm:px-6 bg-[#0d0d0d] glass shrink-0">
      {/* Left: Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="md:hidden text-zinc-500 hover:text-white transition-smooth"
          aria-label="Toggle sidebar"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <h1 className="text-sm sm:text-base font-medium text-zinc-200">
          {title}
        </h1>
      </div>

      {/* Right: Search */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600"
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search..."
            className="w-32 sm:w-48 lg:w-64 bg-zinc-900/60 border border-zinc-800 rounded-lg pl-9 pr-3 py-1.5 text-[13px] text-zinc-300 placeholder-zinc-600 focus:border-zinc-700 focus:bg-zinc-900 transition-smooth"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>
        {/* Connection status */}
        <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-zinc-600">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500/70 animate-pulse-soft" />
          <span>API Live</span>
        </div>

        {/* Session indicator + sign out */}
        {user && (
          <div className="relative">
            <button
              onClick={() => setMenuOpen((o) => !o)}
              className="flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900/60 px-2.5 py-1.5 text-xs text-zinc-300 transition hover:border-zinc-700"
              aria-label="Account"
            >
              <div className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-700 text-[10px] font-semibold text-zinc-100">
                {(user.email || "U").charAt(0).toUpperCase()}
              </div>
              <span className="hidden max-w-[120px] truncate sm:inline">{user.email}</span>
            </button>
            {menuOpen && (
              <div
                className="absolute right-0 top-9 z-50 w-44 rounded-lg border border-zinc-800 bg-zinc-900 p-1 shadow-xl"
                onMouseLeave={() => setMenuOpen(false)}
              >
                <button
                  onClick={() => {
                    signOut();
                    setMenuOpen(false);
                  }}
                  className="w-full rounded-md px-3 py-2 text-left text-xs text-zinc-300 transition hover:bg-zinc-800"
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
