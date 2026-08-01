import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ create: vi.fn(), read: vi.fn(), update: vi.fn() }));
vi.mock("@/lib/api/outreach", () => ({
  createLiveOutreachDraft: api.create,
  getLiveOutreachDraft: api.read,
  updateLiveOutreachDraft: api.update,
}));

import { LiveOutreachWorkspace } from "@/features/outreach/live-outreach-workspace";
import { completeMentorResponse } from "@/test/fixtures/mentor-response";
import { completeOutreachDraftResponse } from "@/test/fixtures/outreach-response";
import { ApiError } from "@/lib/api/result";

const candidate = completeMentorResponse.candidates[0];

function renderWorkspace(mentor = candidate) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <LiveOutreachWorkspace candidate={mentor} query="clinical AI" />
    </QueryClientProvider>,
  );
}

describe("LiveOutreachWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });
  afterEach(cleanup);

  it("shows grounded metadata and has no sending action", async () => {
    api.create.mockResolvedValue(completeOutreachDraftResponse);
    renderWorkspace();

    fireEvent.click(screen.getByRole("button", { name: "Build grounded draft" }));

    expect(await screen.findByRole("heading", { name: "Outreach draft" })).toBeInTheDocument();
    expect(screen.getByText("Claim-to-evidence map")).toBeInTheDocument();
    expect(screen.getByText(/Model key not configured/)).toBeInTheDocument();
    expect(screen.getByText(/contact, title, current institution/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^send/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy reviewed draft" })).toBeDisabled();
  });

  it("requires a saved version and fresh human review before copy", async () => {
    api.create.mockResolvedValue(completeOutreachDraftResponse);
    api.update.mockImplementation(async ({ body, subject }) => ({
      ...completeOutreachDraftResponse,
      body,
      subject,
      draftVersion: 2,
      evidenceMapStatus: "manual-edit-needs-review" as const,
      revisions: [
        ...completeOutreachDraftResponse.revisions,
        {
          version: 2,
          evidenceMapStatus: "manual-edit-needs-review" as const,
          createdAt: "2026-08-01T17:05:00Z",
        },
      ],
    }));
    renderWorkspace();
    fireEvent.click(screen.getByRole("button", { name: "Build grounded draft" }));

    const subject = await screen.findByLabelText("Subject");
    fireEvent.change(subject, {
      target: { value: "Edited evidence-grounded subject" },
    });
    expect(screen.getByRole("checkbox", { name: /I reviewed the current saved/i })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Save new version" }));

    expect(await screen.findByText("Saved version 2")).toBeInTheDocument();
    const review = screen.getByRole("checkbox", { name: /I reviewed the current saved/i });
    expect(review).toBeEnabled();
    fireEvent.click(review);
    fireEvent.click(screen.getByRole("button", { name: "Copy reviewed draft" }));

    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledOnce());
    expect(screen.getByRole("button", { name: "Copied for your review" })).toBeEnabled();
  });

  it("enforces the two-paper selection limit", () => {
    const papers = [
      candidate.supportingPapers[0],
      {
        ...candidate.supportingPapers[0],
        id: "30000000-0000-4000-8000-000000000002",
        title: "Second supporting paper",
      },
      {
        ...candidate.supportingPapers[0],
        id: "30000000-0000-4000-8000-000000000003",
        title: "Third supporting paper",
      },
    ];
    renderWorkspace({
      ...candidate,
      supportingPaperCount: papers.length,
      supportingPapers: papers,
    });

    fireEvent.click(screen.getByRole("checkbox", { name: /Second supporting paper/ }));
    expect(screen.getByRole("checkbox", { name: /Third supporting paper/ })).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: /Human-centred AI/ }));
    expect(screen.getByRole("checkbox", { name: /Third supporting paper/ })).toBeEnabled();
  });

  it("recovers an optimistic version conflict from the persisted draft", async () => {
    api.create.mockResolvedValue(completeOutreachDraftResponse);
    api.update.mockRejectedValue(
      new ApiError({
        code: "draft_version_conflict",
        message: "This draft has a newer saved version.",
        status: 409,
      }),
    );
    const latest = {
      ...completeOutreachDraftResponse,
      draftVersion: 2,
      subject: "Newer saved evidence-grounded subject",
      revisions: [
        ...completeOutreachDraftResponse.revisions,
        {
          version: 2,
          evidenceMapStatus: "manual-edit-needs-review" as const,
          createdAt: "2026-08-01T17:05:00Z",
        },
      ],
    };
    api.read.mockResolvedValue(latest);
    renderWorkspace();
    fireEvent.click(screen.getByRole("button", { name: "Build grounded draft" }));
    fireEvent.change(await screen.findByLabelText("Subject"), {
      target: { value: "A conflicting local edit" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save new version" }));

    fireEvent.click(await screen.findByRole("button", { name: "Load latest version" }));

    expect(await screen.findByDisplayValue(latest.subject)).toBeInTheDocument();
    expect(screen.getByText("Saved version 2")).toBeInTheDocument();
  });
});
