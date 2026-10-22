import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ discover: vi.fn() }));
vi.mock("@/lib/api/contact", () => ({ findPublicEmail: vi.fn().mockRejectedValue(new Error("Fixture lookup unavailable")) }));

vi.mock("@/lib/api/discovery", () => ({
  discoverOpenAlexPapers: api.discover,
}));

import { LivePaperDiscovery } from "@/features/discovery/live-paper-discovery";

const completeResponse = {
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
  papers: [
    {
      id: "10000000-0000-4000-8000-000000000001",
      openalexId: "W1000000001",
      doi: "10.1234/rbai.1",
      title: "Human-centred AI for clinical decisions",
      publicationYear: 2026,
      publicationDate: "2026-04-12",
      workType: "article",
      language: "en",
      venue: "Journal of Responsible Health AI",
      abstractExcerpt: "A validated abstract excerpt.",
      evidenceStrength: "full-abstract" as const,
      sourceUrl: "https://openalex.org/W1000000001",
      lastVerifiedAt: "2026-08-01T16:00:00Z",
      authors: [
        {
          id: "10000000-0000-4000-8000-000000000002",
          openalexId: "A1000000001",
          orcid: null,
          displayName: "Mira Sen",
          isCorresponding: true,
          sourceUrl: "https://openalex.org/A1000000001",
          institutions: [
            {
              id: "10000000-0000-4000-8000-000000000003",
              openalexId: "I1000000001",
              rorId: null,
              displayName: "Institute for Human-Centred Computing",
              countryCode: "IN",
              city: "Bengaluru",
              sourceUrl: "https://openalex.org/I1000000001",
            },
          ],
        },
      ],
      topics: [
        {
          id: "10000000-0000-4000-8000-000000000004",
          openalexId: "T1000000001",
          displayName: "Clinical Decision Support Systems",
          score: 0.94,
        },
      ],
    },
  ],
};

function renderDiscovery() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <LivePaperDiscovery />
    </QueryClientProvider>,
  );
}

describe("LivePaperDiscovery", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);

  it("renders evidence provenance without claiming Research Bridge ranking", async () => {
    api.discover.mockResolvedValue(completeResponse);
    renderDiscovery();

    fireEvent.click(screen.getByRole("button", { name: "Search papers" }));

    expect(
      await screen.findByRole("heading", { name: "Papers on your topic" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Academic database results")).toBeInTheDocument();
    expect(screen.getByText("Mira Sen")).toBeInTheDocument();
    expect(screen.getByText(/0.94 provider score/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /DOI record/ })).toHaveAttribute(
      "href",
      "https://doi.org/10.1234/rbai.1",
    );
  });

  it("keeps valid papers visible with a partial-source warning", async () => {
    api.discover.mockResolvedValue({
      ...completeResponse,
      status: "partial",
      skippedCount: 1,
      warnings: ["One invalid record was skipped."],
    });
    renderDiscovery();

    fireEvent.click(screen.getByRole("button", { name: "Search papers" }));

    expect(await screen.findByText("OpenAlex returned partial evidence")).toBeInTheDocument();
    expect(screen.getByText("Human-centred AI for clinical decisions")).toBeInTheDocument();
    expect(screen.getByText(/One invalid record was skipped/)).toBeInTheDocument();
  });
});
