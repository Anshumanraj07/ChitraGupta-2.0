"use client";

import React, { useState, useEffect, useCallback } from "react";
import { API_BASE, ProviderHealth } from "@/lib/types";

interface SettingsViewProps {
  providerHealth: ProviderHealth | null;
}

export default function SettingsView({ providerHealth }: SettingsViewProps) {
  const [theme, setTheme] = useState("dark");
  const [language, setLanguage] = useState("en");
  const [memoryEnabled, setMemoryEnabled] = useState(true);
  const [exporting, setExporting] = useState(false);

  const exportData = async () => {
    setExporting(true);
    try {
      const res = await fetch(`${API_BASE}/api/export`);
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `chitragupta-export-${new Date().toISOString().split("T")[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch {
      console.error("Export failed");
    }
    setExporting(false);
  };

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-4 sm:p-6 lg:p-8">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <img src="/logo.jpg" alt="ChitraGupta" className="w-10 h-10 rounded-xl object-cover ring-1 ring-zinc-700" />
          <h2 className="text-xl font-semibold text-white tracking-tight">Settings</h2>
        </div>

        {/* Provider Status */}
        <div className="card p-5">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">Provider Status</h3>
          {providerHealth?.report ? (
            <div className="space-y-2">
              <p className="text-[12px] text-zinc-400">{providerHealth.report.slice(0, 500)}</p>
            </div>
          ) : (
            <p className="text-[12px] text-zinc-600">Loading provider status...</p>
          )}
        </div>

        {/* Appearance */}
        <div className="card p-5">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">Appearance</h3>
          <SettingRow label="Theme">
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="bg-zinc-900/60 border border-zinc-800 rounded-lg px-3 py-1.5 text-[12px] text-zinc-300"
            >
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
          </SettingRow>
          <SettingRow label="Language">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-zinc-900/60 border border-zinc-800 rounded-lg px-3 py-1.5 text-[12px] text-zinc-300"
            >
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="es">Spanish</option>
            </select>
          </SettingRow>
        </div>

        {/* Memory Controls */}
        <div className="card p-5">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">Memory Controls</h3>
          <SettingRow label="Adaptive Memory">
            <Toggle checked={memoryEnabled} onChange={setMemoryEnabled} />
          </SettingRow>
        </div>

        {/* Data Export/Import */}
        <div className="card p-5">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">Data Management</h3>
          <div className="flex gap-2">
            <button onClick={exportData} disabled={exporting} className="btn-ghost px-4 py-2 text-[12px]">
              {exporting ? "Exporting..." : "Export Data"}
            </button>
          </div>
        </div>

        {/* Profile */}
        <div className="card p-5">
          <h3 className="text-sm font-medium text-zinc-300 mb-4">Profile</h3>
          <div className="flex items-center gap-3 mb-4">
            <img src="/logo.jpg" alt="" className="w-12 h-12 rounded-xl object-cover" />
            <div>
              <p className="text-[13px] text-zinc-300">ChitraGupta User</p>
              <p className="text-[11px] text-zinc-600">Beta User</p>
            </div>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="card p-5 border-l-4 border-l-red-500">
          <h3 className="text-sm font-medium text-red-400 mb-4">Danger Zone</h3>
          <p className="text-[12px] text-zinc-500 mb-3">
            Reset all data including memories, tasks, and karma history.
          </p>
          <button className="bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 px-4 py-2 rounded-lg text-[12px] transition-smooth">
            Reset All Data
          </button>
        </div>
      </div>
    </div>
  );
}

function SettingRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-zinc-800 last:border-0">
      <span className="text-[12px] text-zinc-400">{label}</span>
      {children}
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative w-10 h-5 rounded-full transition-smooth ${
        checked ? "bg-orange-500" : "bg-zinc-700"
      }`}
    >
      <div
        className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-smooth ${
          checked ? "left-5" : "left-0.5"
        }`}
      />
    </button>
  );
}