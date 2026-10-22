"use client";

import { useCallback } from "react";
import { z } from "zod";
import { useResearchValue, useResearchController } from "@/features/discovery/research-session";

import { mentorDiscoveryResponseSchema, type MentorDiscoveryResponse } from "@/features/discovery/contracts";
import { outreachDraftResponseSchema, type OutreachDraftResponse } from "@/features/outreach/contracts";
import { getAccessToken } from "@/lib/api/setup";

export type WorkflowPhase = "idle" | "discovering" | "awaiting_selection" | "generating" | "done" | "error";
export interface WorkflowState {
  phase: WorkflowPhase;
  threadId: string | null;
  discoveryResponse: MentorDiscoveryResponse | null;
  discoveryError: string | null;
  draftResponse: OutreachDraftResponse | null;
  draftError: string | null;
  errorMessage: string | null;
}
const initialState: WorkflowState = {
  phase: "idle", threadId: null, discoveryResponse: null, discoveryError: null,
  draftResponse: null, draftError: null, errorMessage: null,
};
const eventSchema = z.object({
  discover_mentors: z.object({
    discovery_response: mentorDiscoveryResponseSchema.optional(),
    discovery_error: z.string().optional(),
  }).optional(),
  generate_draft: z.object({
    draft_response: outreachDraftResponseSchema.optional(),
    draft_error: z.string().optional(),
  }).optional(),
});
type Action =
  | { type: "START" }
  | { type: "THREAD"; id: string }
  | { type: "EVENT"; data: z.infer<typeof eventSchema> }
  | { type: "RESUME" }
  | { type: "COMPLETE" }
  | { type: "ERROR"; message: string }
  | { type: "RESET" };
function reducer(state: WorkflowState, action: Action): WorkflowState {
  switch (action.type) {
    case "START": return { ...initialState, phase: "discovering" };
    case "THREAD": return { ...state, threadId: action.id };
    case "EVENT": return {
      ...state,
      discoveryResponse: action.data.discover_mentors?.discovery_response ?? state.discoveryResponse,
      discoveryError: action.data.discover_mentors?.discovery_error ?? state.discoveryError,
      draftResponse: action.data.generate_draft?.draft_response ?? state.draftResponse,
      draftError: action.data.generate_draft?.draft_error ?? state.draftError,
    };
    case "RESUME": return { ...state, phase: "generating", draftError: null, errorMessage: null };
    case "COMPLETE": {
      const error = state.discoveryError ?? state.draftError;
      if (error) return { ...state, phase: "error", errorMessage: error };
      if (state.draftResponse) return { ...state, phase: "done" };
      if (state.discoveryResponse) return { ...state, phase: "awaiting_selection" };
      return { ...state, phase: "error", errorMessage: "The workflow returned no evidence." };
    }
    case "ERROR": return { ...state, phase: "error", errorMessage: action.message };
    case "RESET": return initialState;
  }
}
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "/backend";

export function useWorkflow() {
  const schema = z.object({
    phase: z.enum(["idle", "discovering", "awaiting_selection", "generating", "done", "error"]),
    threadId: z.string().nullable(), discoveryResponse: mentorDiscoveryResponseSchema.nullable(),
    discoveryError: z.string().nullable(), draftResponse: outreachDraftResponseSchema.nullable(),
    draftError: z.string().nullable(), errorMessage: z.string().nullable(),
  }).transform((value): WorkflowState => ["discovering", "generating"].includes(value.phase)
    ? { ...value, phase: "error", errorMessage: "The page was refreshed. Received evidence is restored; restart unfinished work." }
    : value);
  const [state, setState] = useResearchValue<WorkflowState>("guided-workflow", schema, initialState);
  const dispatch = useCallback((action: Action) => setState((previous) => reducer(previous, action)), [setState]);
  const abortRef = useResearchController("guided-workflow");

  const streamThread = useCallback(async (threadId: string, token: string, controller: AbortController) => {
    const response = await fetch(`${BACKEND}/api/v1/workflow/${threadId}/stream`, {
      headers: { Authorization: `Bearer ${token}` }, signal: controller.signal,
    });
    if (!response.ok || !response.body) throw new Error(`Workflow unavailable (HTTP ${response.status}).`);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (controller.signal.aborted) return;
        if (done) throw new Error("The connection ended before the workflow finished. Please try again.");
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split(/\r?\n\r?\n/);
        buffer = parts.pop() ?? "";
        for (const part of parts) {
          const name = part.match(/^event:\s*(.+)/m)?.[1]?.trim();
          const data = part.split(/\r?\n/).filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
          if (name === "complete") { dispatch({ type: "COMPLETE" }); return; }
          if (!data) continue;
          if (name === "error") {
            const error = z.object({ error: z.string() }).parse(JSON.parse(data));
            throw new Error(error.error);
          }
          const parsed = eventSchema.safeParse(JSON.parse(data));
          if (!parsed.success) throw new Error("The workflow returned evidence in an unexpected format.");
          dispatch({ type: "EVENT", data: parsed.data });
        }
      }
    } finally {
      await reader.cancel();
      reader.releaseLock();
    }
  }, [dispatch]);

  const start = useCallback(async (query: string, paperLimit = 20, candidateLimit = 12) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    dispatch({ type: "START" });
    try {
      const token = await getAccessToken();
      if (!token) throw new Error("Sign in to start a workflow.");
      const response = await fetch(`${BACKEND}/api/v1/workflow/start`, {
        method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ query, paperLimit, candidateLimit }), signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Unable to start workflow (HTTP ${response.status}).`);
      const { thread_id: id } = z.object({ thread_id: z.string().uuid() }).parse(await response.json());
      if (controller.signal.aborted) return;
      dispatch({ type: "THREAD", id });
      await streamThread(id, token, controller);
    } catch (error) {
      if (!controller.signal.aborted) dispatch({ type: "ERROR", message: error instanceof Error ? error.message : "Unable to start workflow." });
    }
  }, [streamThread, abortRef, dispatch]);

  const resume = useCallback(async (mentorId: string, paperIds: string[]) => {
    if (!state.threadId || state.phase !== "awaiting_selection") return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    dispatch({ type: "RESUME" });
    try {
      const token = await getAccessToken();
      if (!token) throw new Error("Sign in to continue this workflow.");
      const response = await fetch(`${BACKEND}/api/v1/workflow/${state.threadId}/resume`, {
        method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ selectedMentorId: mentorId, selectedPaperIds: paperIds }), signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Unable to resume workflow (HTTP ${response.status}).`);
      if (!controller.signal.aborted) await streamThread(state.threadId, token, controller);
    } catch (error) {
      if (!controller.signal.aborted) dispatch({ type: "ERROR", message: error instanceof Error ? error.message : "Unable to resume workflow." });
    }
  }, [state.threadId, state.phase, streamThread, abortRef, dispatch]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ type: "RESET" });
  }, [abortRef, dispatch]);
  return { state, start, resume, reset };
}
