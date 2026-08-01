import type {
  OutreachDraftCreateRequest,
  OutreachDraftUpdateRequest,
} from "@/lib/api/generated";
import { Sdk } from "@/lib/api/generated";
import { client } from "@/lib/api/generated/client.gen";
import {
  outreachDraftResponseSchema,
  type OutreachDraftResponse,
} from "@/features/outreach/contracts";
import { parseApiData } from "@/lib/api/result";

client.setConfig({ baseUrl: "/backend" });
const sdk = new Sdk({ client });

export async function createLiveOutreachDraft({
  generationPreference,
  mentorId,
  paperIds,
  query,
  signal,
}: {
  generationPreference: "auto" | "deterministic";
  mentorId: string;
  paperIds: string[];
  query: string;
  signal?: AbortSignal;
}): Promise<OutreachDraftResponse> {
  const body = {
    generationPreference,
    mentorId,
    paperIds,
    query,
  } satisfies OutreachDraftCreateRequest;
  const result = await sdk.createOutreachDraftApiV1OutreachDraftsPost({
    body,
    signal,
  });
  return parseApiData(result, outreachDraftResponseSchema);
}

export async function getLiveOutreachDraft({
  draftId,
  signal,
}: {
  draftId: string;
  signal?: AbortSignal;
}): Promise<OutreachDraftResponse> {
  const result = await sdk.readOutreachDraftApiV1OutreachDraftsDraftIdGet({
    path: { draft_id: draftId },
    signal,
  });
  return parseApiData(result, outreachDraftResponseSchema);
}

export async function updateLiveOutreachDraft({
  body: draftBody,
  draftId,
  expectedVersion,
  signal,
  subject,
}: {
  body: string;
  draftId: string;
  expectedVersion: number;
  signal?: AbortSignal;
  subject: string;
}): Promise<OutreachDraftResponse> {
  const body = {
    body: draftBody,
    expectedVersion,
    subject,
  } satisfies OutreachDraftUpdateRequest;
  const result = await sdk.updateOutreachDraftApiV1OutreachDraftsDraftIdPut({
    body,
    path: { draft_id: draftId },
    signal,
  });
  return parseApiData(result, outreachDraftResponseSchema);
}
