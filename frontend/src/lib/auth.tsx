/*!
 * ChitraGupta 2.0 — Frontend Auth Context
 * Supabase-backed auth with session restore, refresh, and route guards.
 * Wraps the app; exposes useAuth() for protected screens.
 */
"use client";

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { createClient, SupabaseClient, Session, User } from "@supabase/supabase-js";

export interface AuthState {
  user: User | null;
  session: Session | null;
  loading: boolean;
  error: string | null;
}

export interface AuthContextValue extends AuthState {
  supabase: SupabaseClient | null;
  signIn: (email: string, password: string) => Promise<{ error: string | null }>;
  signUp: (email: string, password: string) => Promise<{ error: string | null }>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

interface WindowWithEnv extends Window {
  ENV?: { SUPABASE_URL?: string; SUPABASE_ANON_KEY?: string };
}

function getSupabaseEnv(): { url: string; anonKey: string } | null {
  // Public env vars in Next.js are prefixed with NEXT_PUBLIC_
  // Also support VITE_ prefixes for flexibility.
  const url =
    (typeof process !== "undefined" && (process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.VITE_SUPABASE_URL)) ||
    (typeof window !== "undefined" && (window as WindowWithEnv).ENV?.SUPABASE_URL) ||
    "";
  const anonKey =
    (typeof process !== "undefined" && (process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.VITE_SUPABASE_ANON_KEY)) ||
    (typeof window !== "undefined" && (window as WindowWithEnv).ENV?.SUPABASE_ANON_KEY) ||
    "";
  if (!url || !anonKey) return null;
  return { url, anonKey };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, session: null, loading: true, error: null });
  const [supabase, setSupabase] = useState<SupabaseClient | null>(null);

  // Initialize client + restore session on mount
  useEffect(() => {
    const env = getSupabaseEnv();
    if (!env) {
      // No Supabase env — degrade gracefully: no auth, app runs anonymous.
      setState({ user: null, session: null, loading: false, error: null });
      // eslint-disable-next-line react-hooks/exhaustive-deps
      return;
    }
    const client = createClient(env.url, env.anonKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
    });
    setSupabase(client);

    // Restore existing session
    (async () => {
      try {
        const { data, error } = await client.auth.getSession();
        if (error) {
          setState({ user: null, session: null, loading: false, error: error.message });
          return;
        }
        if (data.session) {
          setState({ user: data.session.user, session: data.session, loading: false, error: null });
        } else {
          setState({ user: null, session: null, loading: false, error: null });
        }
      } catch (e: any) {
        setState({ user: null, session: null, loading: false, error: e?.message || "Session restore failed" });
      }
    })();

    // Listen for auth state changes (token refresh, sign in/out in other tabs)
    const { data: sub } = client.auth.onAuthStateChange((_event, session) => {
      setState((s) => ({
        ...s,
        session,
        user: session?.user ?? null,
        loading: false,
        error: null,
      }));
    });

    return () => sub.subscription.unsubscribe();
  }, []);

  const signIn = useCallback(
    async (email: string, password: string) => {
      if (!supabase) return { error: "Auth not initialized" };
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) return { error: error.message };
      setState({ user: data.user, session: data.session, loading: false, error: null });
      return { error: null };
    },
    [supabase]
  );

  const signUp = useCallback(
    async (email: string, password: string) => {
      if (!supabase) return { error: "Auth not initialized" };
      const { data, error } = await supabase.auth.signUp({ email, password });
      if (error) return { error: error.message };
      // If email confirmation is disabled, we get a session immediately
      if (data.session) {
        setState({ user: data.user, session: data.session, loading: false, error: null });
      } else {
        setState((s) => ({ ...s, error: "Check your email to confirm your account." }));
      }
      return { error: null };
    },
    [supabase]
  );

  const signOut = useCallback(async () => {
    if (!supabase) {
      setState({ user: null, session: null, loading: false, error: null });
      return;
    }
    await supabase.auth.signOut();
    setState({ user: null, session: null, loading: false, error: null });
  }, [supabase]);

  const refreshSession = useCallback(async () => {
    if (!supabase) return;
    const { data, error } = await supabase.auth.refreshSession();
    if (!error && data.session) {
      setState({ user: data.session.user, session: data.session, loading: false, error: null });
    }
  }, [supabase]);

  const value: AuthContextValue = {
    ...state,
    supabase,
    signIn,
    signUp,
    signOut,
    refreshSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    // Provide a safe default if used outside provider (e.g. SSR build)
    return {
      user: null,
      session: null,
      loading: true,
      error: null,
      supabase: null,
      signIn: async () => ({ error: "Auth not initialized" }),
      signUp: async () => ({ error: "Auth not initialized" }),
      signOut: async () => {},
      refreshSession: async () => {},
    };
  }
  return ctx;
}

/** Resolve the current user id from the JWT, falling back to a passed id. */
export function useUserId(fallback?: string): string {
  const { user } = useAuth();
  return user?.id || fallback || "";
}

/** Build Authorization header for fetch calls to the backend. */
export function useAuthHeaders(): Record<string, string> {
  const { session } = useAuth();
  if (!session?.access_token) return {};
  return { Authorization: `Bearer ${session.access_token}` };
}