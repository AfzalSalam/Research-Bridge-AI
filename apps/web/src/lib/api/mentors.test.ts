import { beforeEach, describe, expect, it, vi } from "vitest";

const generated = vi.hoisted(() => ({ discover: vi.fn(), setConfig: vi.fn() }));

vi.mock("@/lib/api/generated/client.gen", () => ({
  client: { setConfig: generated.setConfig },
}));
vi.mock("@/lib/api/generated", () => ({
  Sdk: class {
    discoverMentorsApiV1DiscoveryMentorsPost = generated.discover;
  },
}));

import { discoverOpenAlexMentors } from "@/lib/api/mentors";
import { completeMentorResponse } from "@/test/fixtures/mentor-response";

describe("mentor discovery API adapter", () => {
  beforeEach(() => vi.clearAllMocks());

  it("sends bounded request data and validates the response", async () => {
    generated.discover.mockResolvedValue({
      data: completeMentorResponse,
      error: undefined,
    });

    await expect(
      discoverOpenAlexMentors({ query: "clinical AI", paperLimit: 20 }),
    ).resolves.toEqual(completeMentorResponse);
    expect(generated.discover).toHaveBeenCalledWith({
      body: { candidateLimit: 12, paperLimit: 20, query: "clinical AI" },
      signal: undefined,
    });
  });

  it("rejects an unsupported public overall score", async () => {
    generated.discover.mockResolvedValue({
      data: {
        ...completeMentorResponse,
        policy: { ...completeMentorResponse.policy, scoreVisibility: "overall" },
      },
      error: undefined,
    });

    await expect(
      discoverOpenAlexMentors({ query: "clinical AI", paperLimit: 20 }),
    ).rejects.toMatchObject({ code: "contract_mismatch" });
  });
});
