import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  createApplication: vi.fn(),
  listSaved: vi.fn(),
  remove: vi.fn(),
  save: vi.fn(),
  search: vi.fn(),
}));

vi.mock("@/lib/api/opportunities", () => ({
  listSavedLiveOpportunities: api.listSaved,
  removeLiveOpportunity: api.remove,
  saveLiveOpportunity: api.save,
  searchLiveOpportunities: api.search,
}));

vi.mock("@/lib/api/applications", () => ({
  createLiveApplication: api.createApplication,
}));

import { LiveOpportunities } from "@/features/opportunities/live-opportunities";
import { completeOpportunityResponse } from "@/test/fixtures/opportunity-response";

function renderWorkspace() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <LiveOpportunities />
    </QueryClientProvider>,
  );
}

describe("LiveOpportunities", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listSaved.mockResolvedValue([]);
  });
  afterEach(cleanup);

  it("shows source evidence and keeps unknown fields explicit without ranking", async () => {
    api.search.mockResolvedValue(completeOpportunityResponse);
    renderWorkspace();

    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText("Research Internship, Robotics")).toBeInTheDocument();
    expect(screen.getAllByText("Unclear").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText(/No suitability score was calculated/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Official application/ })).toHaveAttribute(
      "href",
      completeOpportunityResponse.results[0].applicationUrl,
    );
  });

  it("requires an explicit save before tracking", async () => {
    api.search.mockResolvedValue(completeOpportunityResponse);
    api.save.mockResolvedValue({
      savedAt: "2026-08-01T12:00:00Z",
      opportunity: { ...completeOpportunityResponse.results[0], isSaved: true },
    });
    api.createApplication.mockResolvedValue({
      id: "40000000-0000-4000-8000-000000000001",
      opportunityId: completeOpportunityResponse.results[0].id,
    });
    renderWorkspace();
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    const trackBeforeSave = await screen.findByRole("button", { name: "Track" });
    expect(trackBeforeSave).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(
      await screen.findByRole("button", { name: "Saved · remove" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Track" }));
    expect(await screen.findByRole("button", { name: "Tracked" })).toBeDisabled();
    expect(api.createApplication).toHaveBeenCalledWith(
      { opportunityId: completeOpportunityResponse.results[0].id },
      expect.any(Object),
    );
  });
});
