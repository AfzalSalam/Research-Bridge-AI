import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useWorkflow } from "@/features/workflow/use-workflow";
import { completeMentorResponse } from "@/test/fixtures/mentor-response";
import { completeOutreachDraftResponse } from "@/test/fixtures/outreach-response";

vi.mock("@/lib/api/setup", () => ({ getAccessToken: async () => "test-token" }));
const threadId = "30000000-0000-4000-8000-000000000001";
function stream(event: unknown, complete = true) {
  return new Response(`data: ${JSON.stringify(event)}\n\n${complete ? "event: complete\ndata: {}\n\n" : ""}`, { headers: { "Content-Type": "text/event-stream" } });
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("authenticated guided workflow", () => {
  it("pauses on camelCase mentor evidence, then resumes to a validated draft", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json({ thread_id: threadId }))
      .mockResolvedValueOnce(stream({ discover_mentors: { discovery_response: completeMentorResponse } }))
      .mockResolvedValueOnce(Response.json({ status: "resumed", thread_id: threadId }))
      .mockResolvedValueOnce(stream({ generate_draft: { draft_response: completeOutreachDraftResponse } }));
    vi.stubGlobal("fetch", fetcher);
    const { result } = renderHook(() => useWorkflow(), { wrapper: ({ children }: { children: ReactNode }) => <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider> });
    await act(() => result.current.start("clinical AI"));
    await waitFor(() => expect(result.current.state.phase).toBe("awaiting_selection"));
    expect(result.current.state.discoveryResponse?.candidates[0].displayName).toBe("Mira Sen");
    const mentor = completeMentorResponse.candidates[0];
    await act(() => result.current.resume(mentor.id, [mentor.supportingPapers[0].id]));
    await waitFor(() => expect(result.current.state.phase).toBe("done"));
    expect(result.current.state.draftResponse?.id).toBe(completeOutreachDraftResponse.id);
    expect(fetcher.mock.calls[2][1].headers.Authorization).toBe("Bearer test-token");
  });

  it("rejects malformed evidence rather than rendering undefined mentor fields", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(Response.json({ thread_id: threadId }))
      .mockResolvedValueOnce(stream({ discover_mentors: { discovery_response: { candidates: [{ mentor_id: "wrong-contract" }] } } })));
    const { result } = renderHook(() => useWorkflow(), { wrapper: ({ children }: { children: ReactNode }) => <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider> });
    await act(() => result.current.start("clinical AI"));
    await waitFor(() => expect(result.current.state.phase).toBe("error"));
    expect(result.current.state.discoveryResponse).toBeNull();
    expect(result.current.state.errorMessage).toContain("unexpected format");
  });

  it("does not report success when the stream closes without completion", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(Response.json({ thread_id: threadId }))
      .mockResolvedValueOnce(stream({ discover_mentors: { discovery_response: completeMentorResponse } }, false)));
    const { result } = renderHook(() => useWorkflow(), { wrapper: ({ children }: { children: ReactNode }) => <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider> });
    await act(() => result.current.start("clinical AI"));
    await waitFor(() => expect(result.current.state.phase).toBe("error"));
    expect(result.current.state.errorMessage).toContain("connection ended");
  });
});
