"use client";

import { useQuery } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  type Dispatch,
  type ReactNode,
} from "react";

import {
  demoStateSchema,
  type DemoBootstrap,
  type DemoState,
} from "@/features/demo/contracts";
import { demoReducer, type DemoAction } from "@/features/demo/demo-reducer";
import { DemoApiError, getDemoBootstrap } from "@/lib/api/demo";

const STORAGE_KEY = "research-bridge.demo.phase-04.v1";
export const DEMO_BOOTSTRAP_QUERY_KEY = ["demo", "bootstrap", 1] as const;

interface DemoContextValue {
  bootstrapError: DemoApiError | null;
  bootstrapStatus: "loading" | "error" | "ready";
  catalog: DemoBootstrap | null;
  dispatch: Dispatch<DemoAction>;
  hydrated: boolean;
  resetDemo: () => void;
  retryBootstrap: () => void;
  state: DemoState | null;
  storageWarning: string | null;
}

interface ReadyDemoContextValue extends DemoContextValue {
  bootstrapStatus: "ready";
  catalog: DemoBootstrap;
  hydrated: true;
  state: DemoState;
}

const DemoContext = createContext<DemoContextValue | null>(null);

function isCatalogCompatible(state: DemoState, catalog: DemoBootstrap): boolean {
  const mentorById = new Map(catalog.mentors.map((mentor) => [mentor.id, mentor]));
  const opportunityIds = new Set(
    catalog.opportunities.map((opportunity) => opportunity.id),
  );
  if (state.selectedMentorId && !mentorById.has(state.selectedMentorId)) return false;
  if (state.discovery.mentorIds.some((id) => !mentorById.has(id))) return false;
  if (state.savedOpportunityIds.some((id) => !opportunityIds.has(id))) return false;

  const papersBelongToMentor = (mentorId: string, paperIds: string[]) => {
    const mentor = mentorById.get(mentorId);
    if (!mentor) return false;
    const validPaperIds = new Set(mentor.papers.map((paper) => paper.id));
    return paperIds.every((paperId) => validPaperIds.has(paperId));
  };

  if (
    !Object.entries(state.selectedPaperIds).every(([mentorId, paperIds]) =>
      papersBelongToMentor(mentorId, paperIds),
    )
  ) {
    return false;
  }
  if (
    state.drafts.some(
      (draft) => !papersBelongToMentor(draft.mentorId, draft.paperIds),
    )
  ) {
    return false;
  }
  return state.applications.every((application) =>
    application.targetType === "mentor"
      ? mentorById.has(application.targetId)
      : opportunityIds.has(application.targetId),
  );
}

function asApiError(error: unknown): DemoApiError {
  if (error instanceof DemoApiError) return error;
  return new DemoApiError({
    code: "unexpected_client_error",
    message: "The demo catalog could not be loaded.",
  });
}

export function DemoProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(demoReducer, null);
  const [storageWarning, reportStorageWarning] = useReducer(
    (_current: string | null, warning: string | null) => warning,
    null,
  );
  const initializedCatalog = useRef<DemoBootstrap | null>(null);
  const bootstrapQuery = useQuery({
    queryKey: DEMO_BOOTSTRAP_QUERY_KEY,
    queryFn: ({ signal }) => getDemoBootstrap(signal),
    retry: 1,
    staleTime: Number.POSITIVE_INFINITY,
  });

  useEffect(() => {
    const catalog = bootstrapQuery.data;
    if (!catalog || initializedCatalog.current === catalog) return;
    initializedCatalog.current = catalog;

    try {
      const storedState = window.sessionStorage.getItem(STORAGE_KEY);
      if (storedState) {
        const parsed = demoStateSchema.safeParse(JSON.parse(storedState));
        if (parsed.success && isCatalogCompatible(parsed.data, catalog)) {
          dispatch({
            type: "hydrate",
            state: { ...parsed.data, profile: catalog.profile },
          });
          return;
        }
        window.sessionStorage.removeItem(STORAGE_KEY);
        reportStorageWarning(
          "An incompatible saved demo was discarded and replaced with the current API catalog.",
        );
      }
    } catch {
      try {
        window.sessionStorage.removeItem(STORAGE_KEY);
      } catch {
        // Storage may be completely unavailable; the in-memory demo still works.
      }
      reportStorageWarning(
        "Browser session storage is unavailable; changes will last only until this page reloads.",
      );
    }
    dispatch({ type: "initialize", profile: catalog.profile });
  }, [bootstrapQuery.data]);

  const hydrated = state !== null && bootstrapQuery.data !== undefined;

  useEffect(() => {
    if (!hydrated || state === null) return;
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      reportStorageWarning(
        "Browser session storage is unavailable; changes will last only until this page reloads.",
      );
    }
  }, [hydrated, state]);

  const resetDemo = useCallback(() => {
    if (!bootstrapQuery.data) return;
    dispatch({ type: "reset", profile: bootstrapQuery.data.profile });
  }, [bootstrapQuery.data]);

  const retryBootstrap = useCallback(() => {
    void bootstrapQuery.refetch();
  }, [bootstrapQuery]);

  const bootstrapStatus = bootstrapQuery.isError
    ? "error"
    : hydrated
      ? "ready"
      : "loading";
  const value = useMemo<DemoContextValue>(
    () => ({
      bootstrapError: bootstrapQuery.isError
        ? asApiError(bootstrapQuery.error)
        : null,
      bootstrapStatus,
      catalog: bootstrapQuery.data ?? null,
      dispatch,
      hydrated,
      resetDemo,
      retryBootstrap,
      state,
      storageWarning,
    }),
    [
      bootstrapQuery.data,
      bootstrapQuery.error,
      bootstrapQuery.isError,
      bootstrapStatus,
      hydrated,
      resetDemo,
      retryBootstrap,
      state,
      storageWarning,
    ],
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

export function useReadyDemoStore(): ReadyDemoContextValue {
  const context = useDemoStore();
  if (
    !context.hydrated ||
    context.state === null ||
    context.catalog === null ||
    context.bootstrapStatus !== "ready"
  ) {
    throw new Error("The demo store was read before its API catalog was ready.");
  }
  return context as ReadyDemoContextValue;
}
