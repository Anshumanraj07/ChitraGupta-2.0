"use client";

import React, { useState, useMemo, useCallback } from "react";
import type { Task } from "@/lib/types";
import { API_BASE } from "@/lib/types";

interface TasksViewProps {
  tasks: Task[];
  onUpdate: () => void;
  searchQuery: string;
}

type ViewMode = "list" | "kanban";
type SortBy = "priority" | "created" | "title";

export default function TasksView({ tasks, onUpdate, searchQuery }: TasksViewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [sortBy, setSortBy] = useState<SortBy>("priority");
  const [filterPriority, setFilterPriority] = useState<string>("all");
  const [filterDiscipline, setFilterDiscipline] = useState<string>("all");
  const [showCompleted, setShowCompleted] = useState(false);
  const [selectedTasks, setSelectedTasks] = useState<number[]>([]);
  const [isMounted, setIsMounted] = useState(false);

  React.useEffect(() => setIsMounted(true), []);

  const filteredTasks = useMemo(() => {
    let result = [...tasks];

    if (!showCompleted) result = result.filter((t) => !t.completed);
    if (filterPriority !== "all") result = result.filter((t) => t.priority === filterPriority);
    if (filterDiscipline !== "all") result = result.filter((t) => t.discipline === filterDiscipline);
    if (searchQuery) {
      result = result.filter((t) =>
        t.title.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    result.sort((a, b) => {
      if (sortBy === "priority") {
        const order = { high: 0, medium: 1, low: 2 };
        return (order[a.priority as keyof typeof order] ?? 3) - (order[b.priority as keyof typeof order] ?? 3);
      }
      if (sortBy === "title") return a.title.localeCompare(b.title);
      return 0; // 'created' - already sorted from API
    });

    return result;
  }, [tasks, showCompleted, filterPriority, filterDiscipline, searchQuery, sortBy]);

  const kanbanColumns = useMemo(() => {
    return {
      high: filteredTasks.filter((t) => t.priority === "high"),
      medium: filteredTasks.filter((t) => t.priority === "medium"),
      low: filteredTasks.filter((t) => t.priority === "low"),
    };
  }, [filteredTasks]);

  const toggleTask = useCallback(async (taskId: number, currentCompleted: boolean) => {
    try {
      await fetch(`${API_BASE}/api/tasks/${taskId}?completed=${!currentCompleted}`, {
        method: "PATCH",
      });
      onUpdate();
    } catch {
      console.error("Failed to toggle task");
    }
  }, [onUpdate]);

  const toggleSelect = (taskId: number) => {
    setSelectedTasks((prev) =>
      prev.includes(taskId) ? prev.filter((id) => id !== taskId) : [...prev, taskId]
    );
  };

  const bulkComplete = async () => {
    for (const id of selectedTasks) {
      await toggleTask(id, false);
    }
    setSelectedTasks([]);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="px-4 sm:px-6 py-3 border-b border-zinc-800 flex flex-wrap items-center gap-2 glass">
        {/* View toggle */}
        <div className="flex items-center gap-0.5 bg-zinc-900/60 rounded-lg p-0.5 border border-zinc-800">
          <ToggleBtn active={viewMode === "list"} onClick={() => setViewMode("list")}>
            List
          </ToggleBtn>
          <ToggleBtn active={viewMode === "kanban"} onClick={() => setViewMode("kanban")}>
            Kanban
          </ToggleBtn>
        </div>

        {/* Filters */}
        <select
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value)}
          className="bg-zinc-900/60 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-[12px] text-zinc-300 focus:border-zinc-700"
        >
          <option value="all">All Priority</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <select
          value={filterDiscipline}
          onChange={(e) => setFilterDiscipline(e.target.value)}
          className="bg-zinc-900/60 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-[12px] text-zinc-300 focus:border-zinc-700"
        >
          <option value="all">All Discipline</option>
          <option value="physical">Physical</option>
          <option value="mental">Mental</option>
          <option value="spiritual">Spiritual</option>
        </select>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as SortBy)}
          className="bg-zinc-900/60 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-[12px] text-zinc-300 focus:border-zinc-700"
        >
          <option value="priority">Sort: Priority</option>
          <option value="title">Sort: Title</option>
          <option value="created">Sort: Created</option>
        </select>

        <label className="flex items-center gap-1.5 text-[12px] text-zinc-500 cursor-pointer">
          <input
            type="checkbox"
            checked={showCompleted}
            onChange={() => setShowCompleted(!showCompleted)}
            className="accent-orange-500"
          />
          Show Completed
        </label>

        {/* Task count */}
        <span className="ml-auto text-[11px] text-zinc-600">
          {filteredTasks.length} {filteredTasks.length === 1 ? "task" : "tasks"}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-4 sm:p-6">
        {filteredTasks.length === 0 ? (
          <div className="empty-state h-full">
            <img src="/logo.jpg" alt="" className="w-14 h-14 rounded-xl object-cover mb-3 opacity-40" />
            <p className="text-sm text-zinc-600">No tasks found</p>
            <p className="text-[11px] text-zinc-700 mt-1">Try chatting with the coach to generate tasks</p>
          </div>
        ) : viewMode === "list" ? (
          <div className="max-w-3xl mx-auto space-y-2">
            {/* Bulk actions */}
            {selectedTasks.length > 0 && (
              <div className="card p-3 flex items-center justify-between animate-fade-in">
                <span className="text-[12px] text-zinc-400">{selectedTasks.length} selected</span>
                <div className="flex gap-2">
                  <button onClick={bulkComplete} className="btn-primary text-[11px] px-3 py-1.5">
                    Complete All
                  </button>
                  <button onClick={() => setSelectedTasks([])} className="btn-ghost text-[11px] px-3 py-1.5">
                    Clear
                  </button>
                </div>
              </div>
            )}

            {filteredTasks.map((task) => (
              <TaskListItem
                key={task.id}
                task={task}
                onToggle={() => toggleTask(task.id, task.completed)}
                isSelected={selectedTasks.includes(task.id)}
                onSelect={() => toggleSelect(task.id)}
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 h-full">
            <KanbanColumn title="High Priority" tasks={kanbanColumns.high} color="red" onToggle={toggleTask} />
            <KanbanColumn title="Medium" tasks={kanbanColumns.medium} color="yellow" onToggle={toggleTask} />
            <KanbanColumn title="Low" tasks={kanbanColumns.low} color="zinc" onToggle={toggleTask} />
          </div>
        )}
      </div>
    </div>
  );
}

function ToggleBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-md text-[12px] transition-smooth ${
        active ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"
      }`}
    >
      {children}
    </button>
  );
}

function TaskListItem({ task, onToggle, isSelected, onSelect }: {
  task: Task;
  onToggle: () => void;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const priorityColor =
    task.priority === "high" ? "border-l-red-500" :
    task.priority === "medium" ? "border-l-yellow-500" :
    "border-l-zinc-600";

  return (
    <div className={`card border-l-4 ${priorityColor} ${isSelected ? "ring-1 ring-orange-500" : ""} animate-fade-in`}>
      <div className="flex items-center gap-3 px-4 py-3">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onSelect}
          className="accent-orange-500 shrink-0"
        />
        <input
          type="checkbox"
          checked={task.completed}
          onChange={onToggle}
          className="accent-green-500 shrink-0"
        />
        <div className="flex-1 min-w-0 cursor-pointer" onClick={() => setExpanded(!expanded)}>
          <span className={`text-[13px] ${task.completed ? "line-through text-zinc-700" : "text-zinc-200"}`}>
            {task.title}
          </span>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded-full ${
          task.priority === "high" ? "bg-red-500/20 text-red-400" :
          task.priority === "medium" ? "bg-yellow-500/20 text-yellow-400" :
          "bg-zinc-700 text-zinc-400"
        }`}>
          {task.priority}
        </span>
        <span className="text-[10px] text-zinc-600 capitalize hidden sm:inline">{task.discipline}</span>
        {(task.sub_tasks.length > 0 || task.execution_tips.length > 0) && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-zinc-600 hover:text-zinc-400 transition-smooth"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ transform: expanded ? "rotate(180deg)" : "", transition: "transform 0.2s" }}>
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
        )}
      </div>
      {expanded && (task.sub_tasks.length > 0 || task.execution_tips.length > 0) && (
        <div className="px-4 pb-3 pt-0 space-y-2 animate-fade-in">
          {task.sub_tasks.length > 0 && (
            <div>
              <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-1">Sub Tasks</p>
              <ul className="space-y-1">
                {task.sub_tasks.map((st, i) => (
                  <li key={i} className="text-[12px] text-zinc-500 flex gap-1.5">
                    <span className="text-zinc-700">◦</span>
                    {st}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {task.execution_tips.length > 0 && (
            <div>
              <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-1">Tips</p>
              {task.execution_tips.map((tip, i) => (
                <p key={i} className="text-[11px] text-zinc-500 italic">→ {tip}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function KanbanColumn({ title, tasks, color, onToggle }: {
  title: string;
  tasks: Task[];
  color: string;
  onToggle: (id: number, completed: boolean) => void;
}) {
  const colorMap: Record<string, string> = {
    red: "border-t-red-500",
    yellow: "border-t-yellow-500",
    zinc: "border-t-zinc-500",
  };

  return (
    <div className={`card border-t-4 ${colorMap[color]} flex flex-col max-h-full overflow-hidden`}>
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <h3 className="text-[13px] font-medium text-zinc-300">{title}</h3>
        <span className="text-[11px] text-zinc-600 bg-zinc-800 px-2 py-0.5 rounded-full">
          {tasks.length}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto scrollbar-thin p-2 space-y-2">
        {tasks.map((task) => (
          <div key={task.id} className="card p-3 animate-fade-in hover:border-zinc-700">
            <p className="text-[13px] text-zinc-200 mb-2">{task.title}</p>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={task.completed}
                onChange={() => onToggle(task.id, task.completed)}
                className="accent-green-500"
              />
              <span className="text-[10px] text-zinc-600 capitalize">{task.discipline}</span>
              {task.sub_tasks.length > 0 && (
                <span className="text-[10px] text-zinc-600">
                  {task.sub_tasks.length} steps
                </span>
              )}
            </div>
          </div>
        ))}
        {tasks.length === 0 && (
          <p className="text-[11px] text-zinc-700 text-center py-4">No tasks</p>
        )}
      </div>
    </div>
  );
}