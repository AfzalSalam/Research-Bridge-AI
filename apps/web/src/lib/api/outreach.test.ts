import { beforeEach, describe, expect, it, vi } from "vitest";

const generated = vi.hoisted(() => ({
  create: vi.fn(),
  read: vi.fn(),
  setConfig: vi.fn(),
  update: vi.fn(),
}));

vi.mock("@/lib/api/generated/client.gen", () => ({
  client: { setConfig: generated.setConfig },
}));
vi.mock("@/lib/api/generated", () => ({
  Sdk: class {
    createOutreachDraftApiV1OutreachDraftsPost = generated.create;
    readOutreachDraftApiV1OutreachDraftsDraftIdGet = generated.read;
    updateOutreachDraftApiV1OutreachDraftsDraftIdPut = generated.update;
  },
}));

import {
  createLiveOutreachDraft,
  getLiveOutreachDraft,
  updateLiveOutreachDraft,
} from "@/lib/api/outreach";
import { completeOutreachDraftResponse } from "@/test/fixtures/outreach-response";

describe("live outreach API adapter", () => {
  beforeEach(() => vi.clearAllMocks());

  it("sends only selection IDs and validates the created draft", async () => {
    generated.create.mockResolvedValue({
      data: completeOutreachDraftResponse,
      error: undefined,
    });

    await expect(
      createLiveOutreachDraft({
        generationPreference: "auto",
        mentorId: completeOutreachDraftResponse.mentorId,
        paperIds: [completeOutreachDraftResponse.selectedPapers[0].id],
        query: "clinical AI",
      }),
    ).resolves.toEqual(completeOutreachDraftResponse);
    expect(generated.create).toHaveBeenCalledWith({
      body: {
        generationPreference: "auto",
        mentorId: completeOutreachDraftResponse.mentorId,
        paperIds: [completeOutreachDraftResponse.selectedPapers[0].id],
        query: "clinical AI",
      },
      signal: undefined,
    });
  });

  it("loads a persisted draft through the checked contract", async () => {
    generated.read.mockResolvedValue({
      data: completeOutreachDraftResponse,
      error: undefined,
    });

    await expect(
      getLiveOutreachDraft({ draftId: completeOutreachDraftResponse.id }),
    ).resolves.toEqual(completeOutreachDraftResponse);
    expect(generated.read).toHaveBeenCalledWith({
      path: { draft_id: completeOutreachDraftResponse.id },
      signal: undefined,
    });
  });

  it("sends an expected version and rejects a sendable contract", async () => {
    generated.update.mockResolvedValue({
      data: { ...completeOutreachDraftResponse, canSend: true },
      error: undefined,
    });

    await expect(
      updateLiveOutreachDraft({
        body: completeOutreachDraftResponse.body,
        draftId: completeOutreachDraftResponse.id,
        expectedVersion: 1,
        subject: completeOutreachDraftResponse.subject,
      }),
    ).rejects.toMatchObject({ code: "contract_mismatch" });
    expect(generated.update).toHaveBeenCalledWith({
      body: {
        body: completeOutreachDraftResponse.body,
        expectedVersion: 1,
        subject: completeOutreachDraftResponse.subject,
      },
      path: { draft_id: completeOutreachDraftResponse.id },
      signal: undefined,
    });
  });
});
