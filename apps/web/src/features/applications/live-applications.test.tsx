import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ list: vi.fn(), update: vi.fn() }));

vi.mock("@/lib/api/applications", () => ({
  listLiveApplications: api.list,
  updateLiveApplication: api.update,
}));

import { LiveApplications } from "@/features/applications/live-applications";
import type { ApplicationResponse } from "@/features/applications/contracts";

const application: ApplicationResponse = {
  id: "40000000-0000-4000-8000-000000000001",
  opportunityId: "30000000-0000-4000-8000-000000000001",
  targetLabel: "Research Internship, Robotics",
  sourceUrl: "https://job-boards.greenhouse.io/example/jobs/1",
  status: "saved",
  notes: "",
  followUpDate: null,
  version: 1,
  createdAt: "2026-08-01T12:00:00Z",
  updatedAt: "2026-08-01T12:00:00Z",
  events: [
    {
      sequence: 1,
      fromStatus: null,
      toStatus: "saved",
      note: "Added to the tracker.",
      occurredAt: "2026-08-01T12:00:00Z",
    },
  ],
  allowedNextStatuses: ["drafting", "applied", "closed"],
  externalSubmissionPerformed: false,
};

function renderTracker() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <LiveApplications />
    </QueryClientProvider>,
  );
}

describe("LiveApplications", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);

  it("renders a truthful empty state", async () => {
    api.list.mockResolvedValue([]);
    renderTracker();

    expect(
      await screen.findByText("No live applications are being tracked"),
    ).toBeInTheDocument();
    expect(screen.getByText(/never marks an external application/)).toBeInTheDocument();
  });

  it("saves an allowed status with optimistic version metadata", async () => {
    api.list.mockResolvedValue([application]);
    api.update.mockResolvedValue({
      ...application,
      status: "applied",
      notes: "Submitted on the official page.",
      version: 2,
      allowedNextStatuses: ["interviewing", "closed"],
    });
    renderTracker();

    expect(await screen.findByText(application.targetLabel)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Recorded status"), {
      target: { value: "applied" },
    });
    fireEvent.change(screen.getByLabelText("Private notes"), {
      target: { value: "Submitted on the official page." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save tracker update" }));

    await waitFor(() =>
      expect(api.update).toHaveBeenCalledWith(
        {
          applicationId: application.id,
          expectedVersion: 1,
          followUpDate: null,
          notes: "Submitted on the official page.",
          status: "applied",
        },
        expect.any(Object),
      ),
    );
    expect(await screen.findByText("Saved as version 2.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Private notes"), {
      target: { value: "A new unsaved note." },
    });
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /submit application/i })).toBeNull();
  });
});
