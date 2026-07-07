/*!
 * ChitraGupta 2.0 — Auth Screen + Route Guard
 * Shows login/signup when unauthenticated, renders children when authenticated.
 * Gracefully degrades when Supabase env is absent (allows anonymous access).
 */
"use client";

import React, { useState, ReactNode } from "react";
import { useAuth } from "@/lib/auth";

export default function AuthGuard({ children }: { children: ReactNode }) {
  const { user, session, loading, supabase } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const { signIn, signUp, error: ctxError } = useAuth();

  // No Supabase configured → allow app to run in anonymous mode (backward compat)
  if (!supabase && !loading) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0a0a0a] text-zinc-400">
        <div className="animate-pulse text-sm">Restoring your session…</div>
      </div>
    );
  }

  if (user && session) {
    return <>{children}</>;
  }

  // Unauthenticated → show auth screen
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setLocalError(null);
    const fn = mode === "signin" ? signIn : signUp;
    const { error: err } = await fn(email, password);
    setSubmitting(false);
    if (err) setLocalError(err);
  };

  const displayError = localError || ctxError;

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a] px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold text-zinc-100">ChitraGupta 2.0</h1>
          <p className="mt-1 text-sm text-zinc-500">Mind & Action Observer</p>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 shadow-xl backdrop-blur">
          <div className="mb-5 flex rounded-lg bg-zinc-800/50 p-1">
            <button
              type="button"
              onClick={() => setMode("signin")}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
                mode === "signin" ? "bg-zinc-700 text-zinc-100" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => setMode("signup")}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
                mode === "signup" ? "bg-zinc-700 text-zinc-100" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Sign Up
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-zinc-400">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-100 outline-none transition focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-zinc-400">Password</label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-100 outline-none transition focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
                placeholder="••••••••"
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
              />
            </div>

            {displayError && (
              <div className="rounded-lg border border-red-900/50 bg-red-950/30 px-3 py-2 text-xs text-red-300">
                {displayError}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-zinc-100 py-2.5 text-sm font-semibold text-zinc-900 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? "Please wait…" : mode === "signin" ? "Sign In" : "Create Account"}
            </button>
          </form>
        </div>
        <p className="mt-4 text-center text-xs text-zinc-600">
          Your conversations are private and scoped to your account.
        </p>
      </div>
    </div>
  );
}