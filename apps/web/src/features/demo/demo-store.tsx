"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useState,
  type Dispatch,
  type ReactNode,
} from "react";

import { demoStateSchema, type DemoState } from "@/features/demo/contracts";
import { demoReducer, type DemoAction } from "@/features/demo/demo-reducer";
import { createInitialDemoState } from "@/features/demo/fixtures";

const STORAGE_KEY = "research-bridge.demo.phase-03.v1";

interface DemoContextValue {
  dispatch: Dispatch<DemoAction>;
  hydrated: boolean;
  state: DemoState;
  storageWarning: string | null;
}

const DemoContext = createContext<DemoContextValue | null>(null);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(demoReducer, undefined, createInitialDemoState);
  const [hydrated, setHydrated] = useState(false);
  const [storageWarning, reportStorageWarning] = useReducer(
    (_current: string | null, warning: string | null) => warning,
    null,
  );

  useEffect(() => {
    try {
      const storedState = window.sessionStorage.getItem(STORAGE_KEY);
      if (storedState) {
        const parsed = demoStateSchema.safeParse(JSON.parse(storedState));
        if (parsed.success) {
          dispatch({ type: "hydrate", state: parsed.data });
        } else {
          window.sessionStorage.removeItem(STORAGE_KEY);
          reportStorageWarning(
            "An incompatible saved demo was discarded and replaced with validated fixtures.",
          );
        }
      }
    } catch {
      window.sessionStorage.removeItem(STORAGE_KEY);
      reportStorageWarning(
        "An unreadable saved demo was discarded and replaced with validated fixtures.",
      );
    } finally {
      setHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [hydrated, state]);

  const value = useMemo(
    () => ({ dispatch, hydrated, state, storageWarning }),
    [hydrated, state, storageWarning],
  );

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export function useDemoStore(): DemoContextValue {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error("useDemoStore must be used within DemoProvider.");
  }
  return context;
}
