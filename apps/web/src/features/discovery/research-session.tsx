"use client";

import { createContext, useSyncExternalStore, useCallback, useContext, useEffect, useState, useMemo, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { ApiError } from "@/lib/api/result";

const prefix = "research-session-v1:";
const SessionContext = createContext<{
  read: (key: string) => unknown;
  controllers: Map<string, AbortController>;
} | null>(null);

class ResearchSnapshot {
  private values: Record<string, unknown> | null = null;
  constructor(private readonly storageKey: string, private readonly enabled: boolean) {}
  read(key: string): unknown {
    if (!this.enabled || typeof window === "undefined") return undefined;
    if (!this.values) {
      try {
        const parsed = z.record(z.string(), z.unknown()).safeParse(JSON.parse(sessionStorage.getItem(this.storageKey) ?? "{}"));
        this.values = parsed.success ? parsed.data : {};
      } catch { this.values = {}; }
    }
    return this.values[key];
  }
  persist(entries: Record<string, unknown>) {
    // Load earlier route snapshots before merging the currently mounted queries.
    this.read("");
    this.values = { ...this.values, ...entries };
    try { sessionStorage.setItem(this.storageKey, JSON.stringify(this.values)); }
    catch { /* Storage limits leave the in-memory workspace intact. */ }
  }
}

export function ResearchSessionProvider({ identity, children }: { identity: string; children: ReactNode }) {
  const client = useQueryClient();
  const [controllers] = useState(() => new Map<string, AbortController>());
  const storageKey = prefix + identity;
  const privateAccount = !["loading", "anonymous"].includes(identity);
  const [saved] = useState(() => new ResearchSnapshot(storageKey, privateAccount));
  const read = (key: string) => saved.read(key);
  useEffect(() => {
    // Remove previous accounts' snapshots, including after sign-out. The loading
    // phase must not delete the signed-in account's reload snapshot.
    try {
      if (identity !== "loading") {
        for (const key of Object.keys(sessionStorage)) {
          if (key.startsWith(prefix) && key !== storageKey) sessionStorage.removeItem(key);
        }
      }
    } catch { /* Storage may be disabled; in-memory navigation still works. */ }
    const unsubscribe = client.getQueryCache().subscribe((event) => {
      if (!privateAccount || event.query.queryKey[0] !== "research") return;
      const entries: Record<string, unknown> = {};
      for (const query of client.getQueryCache().findAll({ queryKey: ["research"] })) {
        entries[String(query.queryKey[1])] = query.state.data;
      }
      saved.persist(entries);
    });
    const active = controllers;
    return () => { unsubscribe(); active.forEach((controller) => controller.abort()); active.clear(); };
  }, [client, controllers, identity, privateAccount, saved, storageKey]);
  return <SessionContext.Provider value={{ read, controllers }}>{children}</SessionContext.Provider>;
}

export function useResearchValue<T>(key: string, schema: z.ZodType<T>, initial: NoInfer<T>) {
  const client = useQueryClient();
  const session = useContext(SessionContext);
  const queryKey = useMemo(() => ["research", key] as const, [key]);
  const [fallback] = useState(() => initial);
  const readInitial = () => {
    const stored = schema.safeParse(session?.read(key));
    return stored.success ? stored.data : initial;
  };
  useQuery({ queryKey, queryFn: async () => initial, enabled: false, staleTime: Infinity, gcTime: Infinity, initialData: readInitial });
  // Form inputs need synchronous external-store notification. Query observers
  // batch updates, which can briefly restore a checkbox's old controlled value.
  const subscribe = useCallback((notify: () => void) => client.getQueryCache().subscribe((event) => {
    if (event.query.queryKey[0] === "research" && event.query.queryKey[1] === key) notify();
  }), [client, key]);
  const snapshot = useCallback(() => {
    const value = client.getQueryData<T>(queryKey);
    return value === undefined ? fallback : value;
  }, [client, queryKey, fallback]);
  const data = useSyncExternalStore(subscribe, snapshot, () => fallback);
  const set = useCallback((value: T | ((previous: T) => T)) => {
    client.setQueryData<T>(queryKey, (old) => typeof value === "function" ? (value as (previous: T) => T)(old === undefined ? fallback : old) : value);
  }, [client, fallback, queryKey]);
  const get = () => { const value = client.getQueryData<T>(queryKey); return value === undefined ? initial : value; };
  return [data === undefined ? initial : data, set, get] as const;
}

export function useResearchTask<T, V>(key: string, resultSchema: z.ZodType<T>, variablesSchema: z.ZodType<V>, execute: (values: V, signal: AbortSignal, emit: (data: T) => void) => Promise<T | void>) {
  const session = useContext(SessionContext);
  const [local] = useState(() => new Map<string, AbortController>());
  const controllers = session?.controllers ?? local;
  const schema = z.object({ data: resultSchema.nullable(), variables: variablesSchema.nullable(), status: z.enum(["idle", "pending", "success", "error", "cancelled", "interrupted"]), error: z.string().nullable(), startedAt: z.number().nullable() });
  type Task = z.infer<typeof schema>;
  const empty: Task = { data: null, variables: null, status: "idle", error: null, startedAt: null };
  // Persist pending snapshots, but do not pretend their network work survived a reload.
  const restoredSchema = schema.transform((value) => value.status === "pending" ? { ...value, status: "interrupted" as const } : value);
  const [state, set, get] = useResearchValue(key, restoredSchema, empty);
  const mutation = useMutation({ mutationFn: async (values: V) => {
    controllers.get(key)?.abort();
    const controller = new AbortController();
    controllers.set(key, controller);
    set({ ...empty, variables: values, status: "pending", startedAt: Date.now() });
    try {
      const result = await execute(values, controller.signal, (data) => {
        if (!controller.signal.aborted) set((old) => ({ ...old, data }));
      });
      if (!controller.signal.aborted) set((old) => ({ ...old, data: result ?? old.data, status: "success" }));
    } catch (error) {
      if (!controller.signal.aborted) set((old) => ({ ...old, status: "error", error: error instanceof ApiError ? `${error.message}${error.requestId ? ` Request reference: ${error.requestId}.` : ""}` : error instanceof Error ? error.message : "Search failed. Please try again." }));
    } finally {
      if (controllers.get(key) === controller) controllers.delete(key);
    }
  } });
  function cancel() { controllers.get(key)?.abort(); controllers.delete(key); set((old) => ({ ...old, status: "cancelled" })); }
  function clear() { cancel(); set(empty); }
  return { ...state, isPending: state.status === "pending", isError: state.status === "error", mutate: mutation.mutate, cancel, clear, get };
}

export function useResearchController(key: string) {
  const session = useContext(SessionContext);
  const [fallback] = useState(() => new Map<string, AbortController>());
  const map = session?.controllers ?? fallback;
  return useMemo(() => ({
    get current() { return map.get(key) ?? null; },
    set current(value: AbortController | null) { if (value) map.set(key, value); else map.delete(key); },
  }), [key, map]);
}
