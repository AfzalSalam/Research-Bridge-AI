import { beforeEach, describe, expect, it, vi } from "vitest";

const generated = vi.hoisted(() => ({
  discover: vi.fn(),
  setConfig: vi.fn(),
}));

vi.mock("@/lib/api/generated/client.gen", () => ({
  client: { setConfig: generated.setConfig },
}));

vi.mock("@/lib/api/generated", () => ({
  Sdk: class {
    discoverPapersApiV1DiscoveryPapersPost = generated.discover;
  },
}));

import { discoverOpenAlexPapers } from "@/lib/api/discovery";
import { ApiError } from "@/lib/api/result";

const response = {
  status: "complete" as const,
  query: "clinical AI",
  queryKind: "text" as const,
  ordering: "openalex-provider" as const,
  totalProviderResults: 1,
  returnedCount: 1,
  skippedCount: 0,
  warnings: [],
  source: {
    name: "OpenAlex" as const,
    sourceUrl: "https://openalex.org",
    retrievedAt: "2026-08-01T16:00:00Z",
    accessMode: "api-key" as const,
    cacheStatus: "miss" as const,
    rateLimitRemaining: 90,
    rateLimitResetSeconds: 3600,
  },
  papers: [],
};

describe("OpenAlex discovery API adapter", () => {
  beforeEach(() => vi.clearAllMocks());

  it("sends the generated request and validates the response at runtime", async () => {
    generated.discover.mockResolvedValue({ data: response, error: undefined });

    await expect(
      discoverOpenAlexPapers({ query: "clinical AI", limit: 12 }),
    ).resolves.toEqual(response);
    expect(generated.discover).toHaveBeenCalledWith({
      body: { query: "clinical AI", limit: 12 },
      signal: undefined,
    });
  });

  it("rejects generated data that drifts from the runtime contract", async () => {
    generated.discover.mockResolvedValue({
      data: { ...response, ordering: "research-bridge-ranked" },
      error: undefined,
    });

    const promise = discoverOpenAlexPapers({ query: "clinical AI", limit: 12 });
    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(promise).rejects.toMatchObject({ code: "contract_mismatch" });
  });
});
