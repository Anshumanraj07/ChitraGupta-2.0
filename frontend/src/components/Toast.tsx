/*!
 * ChitraGupta 2.0 — Lightweight toast notifications + confirmation dialogs.
 * Global singleton via useToast().show(). No external deps.
 */
"use client";

import React, { createContext, useCallback, useContext, useState, ReactNode, CSSProperties } from "react";

type ToastType = "success" | "error" | "info" | "warn";

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  show: (message: string, type?: ToastType) => void;
  confirm: (message: string, onConfirm: () => void, onCancel?: () => void) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

let _id = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [confirmState, setConfirmState] = useState<{
    message: string;
    onConfirm: () => void;
    onCancel?: () => void;
  } | null>(null);

  const show = useCallback((message: string, type: ToastType = "info") => {
    const id = ++_id;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  const confirm = useCallback((message: string, onConfirm: () => void, onCancel?: () => void) => {
    setConfirmState({ message, onConfirm, onCancel });
  }, []);

  const colors: Record<ToastType, string> = {
    success: "border-green-900/60 bg-green-950/40 text-green-200",
    error: "border-red-900/60 bg-red-950/40 text-red-200",
    info: "border-zinc-700 bg-zinc-900/80 text-zinc-200",
    warn: "border-amber-900/60 bg-amber-950/40 text-amber-200",
  };

  return (
    <ToastContext.Provider value={{ show, confirm }}>
      {children}

      {/* Toast viewport */}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`animate-in slide-in-from-right rounded-lg border px-3.5 py-2.5 shadow-lg backdrop-blur text-[13px] ${colors[t.type]}`}
            style={{ maxWidth: 320 } as CSSProperties}
          >
            {t.message}
          </div>
        ))}
      </div>

      {/* Confirmation dialog */}
      {confirmState && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-xl border border-zinc-800 bg-zinc-900 p-5 shadow-2xl">
            <p className="text-sm text-zinc-200">{confirmState.message}</p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => {
                  confirmState.onCancel?.();
                  setConfirmState(null);
                }}
                className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 transition hover:bg-zinc-800"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  confirmState.onConfirm();
                  setConfirmState(null);
                }}
                className="rounded-lg bg-red-500/90 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-red-500"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  return ctx || { show: () => {}, confirm: () => {} };
}