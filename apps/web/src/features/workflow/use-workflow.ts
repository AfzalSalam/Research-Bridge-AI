"use client";

/**
 * useWorkflow — drives the two-phase placement journey:
 *   1. POST /workflow/start → get thread_id, then GET /workflow/{id}/stream (SSE)
 *   2. After human selects mentor, POST /workflow/{id}/resume → run SSE again for draft
 *
 * Evidence principle: the backend is fully deterministic. We only stream results,
 * never generate scores or claims on the client.
 */

import { useCallback, useReducer, useRef } from "react";
import { supabase } from "@/lib/supabase/client";

// ── State types ────────────────────────────────────────────────────────────────

export type WorkflowPhase =
  | "idle"
  | "discovering"
  | "awaiting_selection"
  | "generating"
  | "done"
  | "error";

export interface WorkflowState {
  phase: WorkflowPhase;
  threadId: string | null;
  // Raw events streamed from the backend
  events: Record<string, unknown>[];
  // Parsed discovery result from the discover_mentors node
  discoveryResponse: Record<string, unknown> | null;
  discoveryError: string | null;
  // Parsed draft result from the generate_draft node
  draftResponse: Record<string, unknown> | null;
  draftError: string | null;
  errorMessage: string | null;
}

type Action =
  | { type: "START" }
  | { type: "THREAD_CREATED"; threadId: string }
  | { type: "EVENT_RECEIVED"; event: Record<string, unknown> }
  | { type: "DISCOVERY_DONE"; response: Record<string, unknown> }
  | { type: "DISCOVERY_ERROR"; error: string }
  | { type: "AWAITING_SELECTION" }
  | { type: "RESUME_START" }
  | { type: "DRAFT_DONE"; response: Record<string, unknown> }
  | { type: "DRAFT_ERROR"; error: string }
  | { type: "WORKFLOW_DONE" }
  | { type: "ERROR"; message: string }
  | { type: "RESET" };

const initialState: WorkflowState = {
  phase: "idle",
  threadId: null,
  events: [],
  discoveryResponse: null,
  discoveryError: null,
  draftResponse: null,
  draftError: null,
  errorMessage: null,
};

function reducer(state: WorkflowState, action: Action): WorkflowState {
  switch (action.type) {
    case "START":
      return { ...initialState, phase: "discovering" };
    case "THREAD_CREATED":
      return { ...state, threadId: action.threadId };
    case "EVENT_RECEIVED":
      return { ...state, events: [...state.events, action.event] };
    case "DISCOVERY_DONE":
      return { ...state, discoveryResponse: action.response };
    case "DISCOVERY_ERROR":
      return { ...state, discoveryError: action.error };
    case "AWAITING_SELECTION":
      return { ...state, phase: "awaiting_selection" };
    case "RESUME_START":
      return { ...state, phase: "generating" };
    case "DRAFT_DONE":
      return { ...state, draftResponse: action.response };
    case "DRAFT_ERROR":
      return { ...state, draftError: action.error };
    case "WORKFLOW_DONE":
      return { ...state, phase: "done" };
    case "ERROR":
      return { ...state, phase: "error", errorMessage: action.message };
    case "RESET":
      return initialState;
    default:
      return state;
  }
}

// ── Hook ───────────────────────────────────────────────────────────────────────

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "/backend";

async function getBearerToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

export function useWorkflow() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const abortRef = useRef<AbortController | null>(null);

  /**
   * Open the SSE stream for a given thread. Processes node-level update events
   * and transitions phase to awaiting_selection once discovery is done.
   */
  const streamThread = useCallback(
    async (threadId: string, onComplete: () => void) => {
      const token = await getBearerToken();
      if (!token) {
        dispatch({ type: "ERROR", message: "Not authenticated." });
        return;
      }

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      const url = `${BACKEND}/api/v1/workflow/${threadId}/stream`;

      // EventSource doesn't support custom headers, so we use fetch + ReadableStream
      let response: Response;
      try {
        response = await fetch(url, {
          headers: { Authorization: `Bearer ${token}` },
          signal: ctrl.signal,
        });
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          dispatch({ type: "ERROR", message: "Network error reaching server." });
        }
        return;
      }

      if (!response.ok || !response.body) {
        dispatch({
          type: "ERROR",
          message: `Server responded ${response.status}`,
        });
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Split by double newlines (SSE message boundary)
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.trim()) continue;

          // Check for named events
          const eventMatch = part.match(/^event:\s*(.+)/m);
          // Extract everything after "data: " (may span multiple chars but JSON is single line)
          const dataMatch = part.match(/^data:\s*(\{.+\})/m);

          if (eventMatch?.[1] === "complete") {
            dispatch({ type: "WORKFLOW_DONE" });
            onComplete();
            return;
          }
          if (eventMatch?.[1] === "error" && dataMatch?.[1]) {
            const parsed = JSON.parse(dataMatch[1]) as { error?: string };
            dispatch({
              type: "ERROR",
              message: parsed.error ?? "Unknown error from server.",
            });
            return;
          }

          if (dataMatch?.[1]) {
            try {
              const event = JSON.parse(dataMatch[1]) as Record<string, unknown>;
              dispatch({ type: "EVENT_RECEIVED", event });

              // Parse node-level updates
              const discoveryUpdate = event["discover_mentors"] as
                | Record<string, unknown>
                | undefined;
              if (discoveryUpdate) {
                if (discoveryUpdate["discovery_response"]) {
                  dispatch({
                    type: "DISCOVERY_DONE",
                    response: discoveryUpdate[
                      "discovery_response"
                    ] as Record<string, unknown>,
                  });
                }
                if (discoveryUpdate["discovery_error"]) {
                  dispatch({
                    type: "DISCOVERY_ERROR",
                    error: discoveryUpdate["discovery_error"] as string,
                  });
                }
              }

              const draftUpdate = event["generate_draft"] as
                | Record<string, unknown>
                | undefined;
              if (draftUpdate) {
                if (draftUpdate["draft_response"]) {
                  dispatch({
                    type: "DRAFT_DONE",
                    response: draftUpdate[
                      "draft_response"
                    ] as Record<string, unknown>,
                  });
                }
                if (draftUpdate["draft_error"]) {
                  dispatch({
                    type: "DRAFT_ERROR",
                    error: draftUpdate["draft_error"] as string,
                  });
                }
              }
            } catch {
              // Non-JSON SSE data — ignore
            }
          }
        }
      }

      // Stream ended naturally (graph returned END after discover_mentors,
      // waiting for selection)
      dispatch({ type: "AWAITING_SELECTION" });
      onComplete();
    },
    []
  );

  /**
   * Phase 1: start a new workflow run, then stream discovery.
   */
  const start = useCallback(
    async (query: string, paperLimit = 20, candidateLimit = 12) => {
      dispatch({ type: "START" });

      const token = await getBearerToken();
      if (!token) {
        dispatch({ type: "ERROR", message: "Sign in to start a workflow." });
        return;
      }

      let threadId: string;
      try {
        const res = await fetch(`${BACKEND}/api/v1/workflow/start`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query,
            paper_limit: paperLimit,
            candidate_limit: candidateLimit,
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as { thread_id: string };
        threadId = data.thread_id;
        dispatch({ type: "THREAD_CREATED", threadId });
      } catch (err) {
        dispatch({
          type: "ERROR",
          message: `Failed to start workflow: ${(err as Error).message}`,
        });
        return;
      }

      await streamThread(threadId, () => {});
    },
    [streamThread]
  );

  /**
   * Phase 2: submit human selection, then stream draft generation.
   */
  const resume = useCallback(
    async (mentorId: string, paperIds: string[]) => {
      const { threadId } = state;
      if (!threadId) return;

      dispatch({ type: "RESUME_START" });

      const token = await getBearerToken();
      if (!token) {
        dispatch({ type: "ERROR", message: "Not authenticated." });
        return;
      }

      try {
        const res = await fetch(
          `${BACKEND}/api/v1/workflow/${threadId}/resume`,
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              selected_mentor_id: mentorId,
              selected_paper_ids: paperIds,
            }),
          }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
      } catch (err) {
        dispatch({
          type: "ERROR",
          message: `Failed to resume workflow: ${(err as Error).message}`,
        });
        return;
      }

      await streamThread(threadId, () => {});
    },
    [state, streamThread]
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ type: "RESET" });
  }, []);

  return { state, start, resume, reset };
}
