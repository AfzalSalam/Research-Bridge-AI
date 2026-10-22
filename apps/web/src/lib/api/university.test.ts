import { afterEach, expect, it, vi } from "vitest";
import { scanUniversityWebsites } from "./university";
vi.mock("./setup", () => ({ getAccessToken: vi.fn().mockResolvedValue("test-token") }));
afterEach(() => vi.unstubAllGlobals());
const form = { query: "machine learning", target: "20" as const, region: "both" as const };
const snapshot = { state: "partial", query: form.query, target: 20, papers: [], sources: [], programs: [], pagesAttempted: 1, pagesRead: 0, elapsedSeconds: 1, budgetSeconds: 120, currentUniversity: null, stopReason: "reviewed_links_exhausted", warnings: [] };
it("decodes split SSE frames and authenticates the request", async () => {
  const text = `data: ${JSON.stringify(snapshot)}\n\n`;
  const fetcher = vi.fn().mockResolvedValue(new Response(new ReadableStream({ start(controller) {
    const bytes = new TextEncoder().encode(text);
    controller.enqueue(bytes.slice(0, 21)); controller.enqueue(bytes.slice(21)); controller.close();
  } })));
  vi.stubGlobal("fetch", fetcher);
  const emit = vi.fn();
  await scanUniversityWebsites(form, new AbortController().signal, emit);
  expect(emit).toHaveBeenCalledWith(snapshot);
  expect(fetcher.mock.calls[0][1].headers.Authorization).toBe("Bearer test-token");
  expect(JSON.parse(fetcher.mock.calls[0][1].body).target).toBe(20);
});
it("reports truncated streams instead of claiming completion", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("data: {")));
  await expect(scanUniversityWebsites(form, new AbortController().signal, vi.fn())).rejects.toThrow("ended early");
});
it("does not replace previous snapshots with a terminal server error", async () => {
  const emit = vi.fn();
  const payload = { ...snapshot, state: "error", warnings: ["Source scan failed."] };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(`data: ${JSON.stringify(payload)}\n\n`)));
  await expect(scanUniversityWebsites(form, new AbortController().signal, emit)).rejects.toThrow("Source scan failed");
  expect(emit).not.toHaveBeenCalled();
});
