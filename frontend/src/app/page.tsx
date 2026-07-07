"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import ChatView from "@/components/views/ChatView";
import DashboardView from "@/components/views/DashboardView";
import TasksView from "@/components/views/TasksView";
import KarmaView from "@/components/views/KarmaView";
import MemoryView from "@/components/views/MemoryView";
import ReviewView from "@/components/views/ReviewView";
import SettingsView from "@/components/views/SettingsView";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import AuthGuard from "@/components/AuthScreen";
import {
  type ViewKey,
  type Task,
  type KarmaData,
  type ProviderHealth,
  API_BASE,
} from "@/lib/types";

export default function Home() {
  const [activeView, setActiveView] = useState<ViewKey>("dashboard");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [karmaData, setKarmaData] = useState<KarmaData | null>(null);
  const [providerHealth, setProviderHealth] = useState<ProviderHealth | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isMobile, setIsMobile] = useState(false);
  const isMounted = useRef(true);

  // Detect mobile
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Auto-collapse sidebar on mobile
  useEffect(() => {
    // eslint-disable-next-line react-hooks/exhaustive-deps
    if (isMobile) setIsSidebarOpen(false);
  }, [isMobile]);

  // Fetch initial data
  const fetchTasks = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tasks`);
      if (res.ok && isMounted.current) {
        const data = await res.json();
        const tasksData = (data.data || data).map((t: Task, i: number) => ({
          ...t,
          id: t.id ?? Date.now() + i,
          completed: t.completed ?? false,
        }));
        setTasks(tasksData);
      }
    } catch (err) {
      console.error("Failed to fetch tasks", err);
    }
  }, []);

  const fetchKarma = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/karma`);
      if (res.ok && isMounted.current) {
        setKarmaData(await res.json());
      }
    } catch (err) {
      console.error("Failed to fetch karma", err);
    }
  }, []);

  const fetchProviderHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/provider-health`);
      if (res.ok && isMounted.current) {
        const data = await res.json();
        setProviderHealth({
          providers: {},
          report: data._report || "",
        });
      }
    } catch (err) {
      console.error("Failed to fetch provider health", err);
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;
    fetchTasks();
    fetchKarma();
    fetchProviderHealth();
    return () => {
      isMounted.current = false;
    };
  }, [fetchTasks, fetchKarma, fetchProviderHealth]);

  const handleTasksUpdate = useCallback(() => {
    fetchTasks();
    fetchKarma();
  }, [fetchTasks, fetchKarma]);

  const viewTitles: Record<ViewKey, string> = {
    dashboard: "Dashboard",
    chat: "Chat",
    tasks: "Tasks",
    karma: "Karma Analytics",
    memory: "Memory Timeline",
    review: "Daily Review",
    settings: "Settings",
  };

  return (
    <AuthGuard>
    <div className="flex h-screen bg-[#0a0a0a] text-zinc-200 overflow-hidden">
      <Sidebar
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen((o) => !o)}
        activeView={activeView}
        onViewChange={(v: ViewKey) => {
          setActiveView(v);
          if (isMobile) setIsSidebarOpen(false);
        }}
        karmaData={karmaData}
        taskCount={tasks.length}
      />

      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <TopBar
          title={viewTitles[activeView]}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onMenuClick={() => setIsSidebarOpen((o) => !o)}
        />

        <div className="flex-1 overflow-hidden">
          {activeView === "dashboard" && (
            <DashboardView
              tasks={tasks}
              karmaData={karmaData}
              onViewChange={setActiveView}
            />
          )}
          {activeView === "chat" && <ChatView onTasksUpdate={handleTasksUpdate} />}
          {activeView === "tasks" && (
            <TasksView
              tasks={tasks}
              onUpdate={handleTasksUpdate}
              searchQuery={searchQuery}
            />
          )}
          {activeView === "karma" && <KarmaView karmaData={karmaData} />}
          {activeView === "memory" && <MemoryView searchQuery={searchQuery} />}
          {activeView === "review" && <ReviewView />}
          {activeView === "settings" && (
            <SettingsView providerHealth={providerHealth} />
          )}
        </div>
      </main>
    </div>
    </AuthGuard>
  );
}
