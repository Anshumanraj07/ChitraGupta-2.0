"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import type { ChatMessage, Task } from "@/lib/types";
import { API_BASE } from "@/lib/types";

interface ChatViewProps {
  onTasksUpdate: () => void;
}

export default function ChatView({ onTasksUpdate }: ChatViewProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "ai",
      content:
        "Welcome to ChitraGupta. I'm your AI coach and mind observer.\n\nTell me about your goals, what's on your mind, or what you'd like to work on today.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedReasoning, setExpandedReasoning] = useState<number | null>(null);
  const [showSplash, setShowSplash] = useState(true);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Hide splash after 1.5s and focus input
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSplash(false);
      inputRef.current?.focus();
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || loading) return;
    const content = input.trim();
    const userMsg: ChatMessage = { role: "user", content };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history = messages
        .slice(-20)
        .map((m) => ({ role: m.role === "ai" ? "assistant" : "user", content: m.content }));

      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: content, history }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const aiMsg: ChatMessage = {
        role: "ai",
        content: data.response || "I'm here — could you elaborate?",
        bias_flag: data.bias_flag,
        bias_description: data.bias_description,
        shadow_perspective: data.shadow_perspective,
        ego_score: data.ego_score,
        ego_labels: data.ego_labels,
        memory_context: data.memory_context,
          tasks: (data.tasks || []).map((t: Task, i: number) => ({
          ...t,
          id: Date.now() + i,
          completed: false,
        })),
      };

      setMessages((prev) => [...prev, aiMsg]);
      if (data.tasks_generated) onTasksUpdate();
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          content: "Something went wrong. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [input, loading, messages, onTasksUpdate]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage();
  };

  return (
    <div className="flex flex-col h-full">
      {/* Splash Screen */}
      {showSplash && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#0a0a0a] animate-fade-in">
          <img
            src="/logo.jpg"
            alt="ChitraGupta"
            className="w-20 h-20 rounded-2xl object-cover ring-2 ring-zinc-800 animate-pulse-soft"
          />
          <h2 className="text-xl font-semibold text-white mt-4">ChitraGupta 2.0</h2>
          <p className="text-sm text-zinc-500 mt-1">AI Operating System</p>
        </div>
      )}

      {/* Message List */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-4 sm:px-6 py-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              msg={msg}
              index={i}
              isExpanded={expandedReasoning === i}
              onToggleReasoning={() =>
                setExpandedReasoning(expandedReasoning === i ? null : i)
              }
            />
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className="flex items-center gap-3 animate-fade-in">
              <img
                src="/logo.jpg"
                alt=""
                className="w-8 h-8 rounded-lg object-cover ring-1 ring-zinc-700"
              />
              <div className="flex items-center gap-1.5">
                <div className="typing-dot w-2 h-2 bg-orange-400 rounded-full" />
                <div className="typing-dot w-2 h-2 bg-orange-400 rounded-full" />
                <div className="typing-dot w-2 h-2 bg-orange-400 rounded-full" />
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
      </div>

      {/* Input Box */}
      <div className="px-4 sm:px-6 py-4 border-t border-zinc-800 glass">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message..."
              disabled={loading}
              className="flex-1 bg-zinc-900/60 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-zinc-200 placeholder-zinc-600 focus:border-zinc-700 transition-smooth"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="btn-primary p-3 rounded-xl shrink-0"
              aria-label="Send message"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </form>
        <p className="text-[11px] text-zinc-600 mt-2 text-center">
          ChitraGupta may make mistakes. Verify important information.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Message Bubble
// ---------------------------------------------------------------------------
function MessageBubble({
  msg,
  index,
  isExpanded,
  onToggleReasoning,
}: {
  msg: ChatMessage;
  index: number;
  isExpanded: boolean;
  onToggleReasoning: () => void;
}) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex gap-3 animate-fade-in ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      {!isUser && (
        <img
          src="/logo.jpg"
          alt="AI"
          className="w-8 h-8 rounded-lg object-cover ring-1 ring-zinc-700 shrink-0"
        />
      )}
      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center text-xs text-zinc-400 shrink-0">
          You
        </div>
      )}

      {/* Content */}
      <div className={`max-w-[80%] ${isUser ? "items-end" : ""}`}>
        {/* Main content */}
        <div
          className={`px-4 py-3 rounded-2xl text-[14px] leading-relaxed markdown-content ${
            isUser
              ? "bg-zinc-800 text-zinc-200 rounded-tr-md"
              : "bg-[#111113] border border-zinc-800 text-zinc-300 rounded-tl-md"
          }`}
        >
          <FormattedContent content={msg.content} />
        </div>

        {/* Reasoning Card (bias / shadow / ego) */}
        {(msg.bias_flag || msg.shadow_perspective || msg.ego_labels?.length) && (
          <div className="mt-2">
            <button
              onClick={onToggleReasoning}
              className="flex items-center gap-1.5 text-[11px] text-zinc-500 hover:text-zinc-300 transition-smooth"
            >
              <svg
                width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
                style={{ transform: isExpanded ? "rotate(90deg)" : "none", transition: "transform 0.2s" }}
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
              <span>Coaching Analysis</span>
            </button>
            {isExpanded && (
              <div className="mt-2 space-y-2 animate-fade-in">
                {msg.bias_flag && msg.bias_description && (
                  <div className="card p-3 border-l-2 border-red-500">
                    <p className="text-[11px] text-red-400 font-medium mb-1">Bias Detected</p>
                    <p className="text-[12px] text-zinc-400">{msg.bias_description}</p>
                  </div>
                )}
                {msg.shadow_perspective && (
                  <div className="card p-3 border-l-2 border-purple-500">
                    <p className="text-[11px] text-purple-400 font-medium mb-1">Shadow Perspective</p>
                    <p className="text-[12px] text-zinc-400">{msg.shadow_perspective}</p>
                  </div>
                )}
                {msg.ego_labels && msg.ego_labels.length > 0 && (
                  <div className="card p-3 border-l-2 border-blue-500">
                    <p className="text-[11px] text-blue-400 font-medium mb-1">Ego Analysis</p>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.ego_labels.map((label, i) => (
                        <span key={i} className="text-[11px] bg-zinc-800 px-2 py-0.5 rounded text-zinc-300">
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {msg.memory_context && (
                  <div className="card p-3 border-l-2 border-green-500">
                    <p className="text-[11px] text-green-400 font-medium mb-1">Memory Context</p>
                    <p className="text-[12px] text-zinc-400">{msg.memory_context}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Task Cards */}
        {msg.tasks && msg.tasks.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-[11px] text-zinc-500 uppercase tracking-wider">
              Generated Tasks
            </p>
            {msg.tasks.map((task, ti) => (
              <TaskCard key={ti} task={task} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Formatted Content (basic markdown)
// ---------------------------------------------------------------------------
function FormattedContent({ content }: { content: string }) {
  // Simple formatting: split by line, render basic markdown
  const lines = content.split("\n");

  return (
    <>
      {lines.map((line, i) => {
        if (line.startsWith("```")) {
          const code = lines.slice(i + 1).join("\n").split("```")[0];
          return (
            <pre key={i}>
              <code>{code}</code>
            </pre>
          );
        }
        if (line.startsWith("- ") || line.startsWith("* ")) {
          const items = content
            .split("\n")
            .filter((l) => l.startsWith("- ") || l.startsWith("* "))
            .map((l) => l.slice(2));
          if (i === lines.findIndex((l) => l.startsWith("- ") || l.startsWith("* "))) {
            return (
              <ul key={i}>
                {items.map((item, j) => (
                  <li key={j}>{item}</li>
                ))}
              </ul>
            );
          }
          return null;
        }
        if (line.startsWith("**") && line.endsWith("**")) {
          return <p key={i}><strong>{line.slice(2, -2)}</strong></p>;
        }
        return <p key={i} className="whitespace-pre-wrap">{line || "\u00A0"}</p>;
      })}
    </>
  );
}

// ---------------------------------------------------------------------------
// Task Card
// ---------------------------------------------------------------------------
function TaskCard({ task }: { task: Task }) {
  return (
    <div className="card p-3 border-l-4" style={{
      borderLeftColor: task.priority === "high" ? "#ef4444" : task.priority === "medium" ? "#f59e0b" : "#71717a"
    }}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-medium text-zinc-200">{task.title}</p>
          {task.sub_tasks && task.sub_tasks.length > 0 && (
            <ul className="mt-2 space-y-1">
              {task.sub_tasks.map((st, i) => (
                <li key={i} className="text-[12px] text-zinc-500 flex gap-1.5">
                  <span className="text-zinc-700">•</span>
                  {st}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <span className={`text-[10px] px-2 py-0.5 rounded-full ${
            task.priority === "high" ? "bg-red-500/20 text-red-400" :
            task.priority === "medium" ? "bg-yellow-500/20 text-yellow-400" :
            "bg-zinc-700 text-zinc-400"
          }`}>
            {task.priority}
          </span>
          <span className="text-[10px] text-zinc-600 capitalize">{task.discipline}</span>
        </div>
      </div>
      {task.execution_tips && task.execution_tips.length > 0 && (
        <div className="mt-2 pt-2 border-t border-zinc-800">
          <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-1">Tips</p>
          {task.execution_tips.map((tip, i) => (
            <p key={i} className="text-[11px] text-zinc-500 italic">→ {tip}</p>
          ))}
        </div>
      )}
    </div>
  );
}