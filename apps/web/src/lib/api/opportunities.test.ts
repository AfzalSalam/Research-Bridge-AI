import { beforeEach, describe, expect, it, vi } from "vitest";

const generated = vi.hoisted(() => ({
  listSaved: vi.fn(),
  remove: vi.fn(),
  save: vi.fn(),
  search: vi.fn(),
  setConfig: vi.fn(),
}));

vi.mock("@/lib/api/generated/client.gen", () => ({
  client: { setConfig: generated.setConfig },
}));

vi.mock("@/lib/api/generated", () => ({
  Sdk: class {
    listSavedOpportunitiesApiV1OpportunitiesSavedGet = generated.listSaved;
    removeSavedOpportunityApiV1OpportunitiesOpportunityIdSaveDelete = generated.remove;
    saveOpportunityApiV1OpportunitiesOpportunityIdSavePost = generated.save;
    searchOpportunitiesApiV1OpportunitiesSearchPost = generated.search;
  },
}));

import { searchLiveOpportunities } from "@/lib/api/opportunities";
import { ApiError } from "@/lib/api/result";
import { completeOpportunityResponse } from "@/test/fixtures/opportunity-response";

describe("verified opportunities API adapter", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses the generated request and validates the no-ranking response", async () => {
    generated.search.mockResolvedValue({
      data: completeOpportunityResponse,
      error: undefined,
    });

    await expect(
      searchLiveOpportunities({
        query: "machine learning",
        countryCode: null,
        workMode: null,
        funding: null,
        includeExpired: false,
        limit: 20,
      }),
    ).resolves.toEqual(completeOpportunityResponse);
    expect(generated.search).toHaveBeenCalledWith({
      body: {
        query: "machine learning",
        countryCode: null,
        workMode: null,
        funding: null,
        includeExpired: false,
        limit: 20,
      },
      signal: undefined,
    });
  });

  it("rejects a response that introduces ranking", async () => {
    generated.search.mockResolvedValue({
      data: { ...completeOpportunityResponse, rankingApplied: true },
      error: undefined,
    });

    const request = searchLiveOpportunities({
      query: "machine learning",
      countryCode: null,
      workMode: null,
      funding: null,
      includeExpired: false,
      limit: 20,
    });
    await expect(request).rejects.toBeInstanceOf(ApiError);
    await expect(request).rejects.toMatchObject({ code: "contract_mismatch" });
  });
});
