import type { OpportunitySearchRequest } from "@/lib/api/generated";
import { z } from "zod";
import { Sdk } from "@/lib/api/generated";
import { client } from "@/lib/api/generated/client.gen";
import {
  opportunitySearchResponseSchema,
  savedOpportunityListResponseSchema,
  savedOpportunitySchema,
  type OpportunitySearchForm,
  type OpportunitySearchResponse,
  type SavedOpportunity,
} from "@/features/opportunities/contracts";
import { parseApiData } from "@/lib/api/result";

client.setConfig({ baseUrl: "/backend" });
const sdk = new Sdk({ client });

export async function searchLiveOpportunities({
  countryCode,
  funding,
  includeExpired,
  limit,
  query,
  signal,
  workMode,
}: OpportunitySearchForm & { signal?: AbortSignal }): Promise<OpportunitySearchResponse> {
  const body = {
    countryCode,
    funding,
    includeExpired,
    limit,
    query,
    workMode,
  } satisfies OpportunitySearchRequest;
  const result = await sdk.searchOpportunitiesApiV1OpportunitiesSearchPost({
    body,
    signal,
  });
  return parseApiData(result, opportunitySearchResponseSchema);
}

export async function saveLiveOpportunity({
  opportunityId,
}: {
  opportunityId: string;
}): Promise<SavedOpportunity> {
  const result = await sdk.saveOpportunityApiV1OpportunitiesOpportunityIdSavePost({
    path: { opportunity_id: opportunityId },
  });
  return parseApiData(result, savedOpportunitySchema);
}

export async function removeLiveOpportunity({
  opportunityId,
}: {
  opportunityId: string;
}): Promise<void> {
  const result =
    await sdk.removeSavedOpportunityApiV1OpportunitiesOpportunityIdSaveDelete({
      path: { opportunity_id: opportunityId },
    });
  if (result.response?.ok) return;
  parseApiData(result, z.never());
}

export async function listSavedLiveOpportunities({
  signal,
}: {
  signal?: AbortSignal;
} = {}): Promise<SavedOpportunity[]> {
  const result = await sdk.listSavedOpportunitiesApiV1OpportunitiesSavedGet({
    signal,
  });
  return parseApiData(result, savedOpportunityListResponseSchema).items;
}
