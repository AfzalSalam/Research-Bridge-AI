import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ discover: vi.fn() }));
vi.mock("@/lib/api/mentors", () => ({ discoverOpenAlexMentors: api.discover }));

import { LiveMentorDiscovery } from "@/features/mentors/live-mentor-discovery";
import { completeMentorResponse } from "@/test/fixtures/mentor-response";

function renderDiscovery() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <LiveMentorDiscovery initialQuery="clinical AI" />
    </QueryClientProvider>,
  );
}

describe("LiveMentorDiscovery", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);

  it("shows policy evidence and keeps employment claims unknown", async () => {
    api.discover.mockResolvedValue(completeMentorResponse);
    renderDiscovery();
    fireEvent.click(screen.getByRole("button", { name: "Find researchers" }));

    expect(
      await screen.findByRole("heading", { name: "Reviewable researcher evidence" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Mira Sen").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Why this candidate appears here" })).toBeInTheDocument();
    expect(screen.getByText("Affiliations at publication")).toBeInTheDocument();
    expect(screen.getByText("Institute for Human-Centred Computing")).toBeInTheDocument();
    expect(screen.getAllByText("Unknown").length).toBeGreaterThanOrEqual(3);
    expect(screen.queryByText(/overall compatibility percentage.*%/i)).not.toBeInTheDocument();
  });

  it("keeps candidates visible beside a partial-source warning", async () => {
    api.discover.mockResolvedValue({
      ...completeMentorResponse,
      status: "partial",
      warnings: ["One invalid provider record was skipped."],
    });
    renderDiscovery();
    fireEvent.click(screen.getByRole("button", { name: "Find researchers" }));

    expect(await screen.findByText("Candidate evidence is partial")).toBeInTheDocument();
    expect(screen.getAllByText("Mira Sen").length).toBeGreaterThan(0);
    expect(screen.getByText(/invalid provider record/)).toBeInTheDocument();
  });
});
