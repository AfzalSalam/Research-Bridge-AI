import type { MentorDiscoveryRequest as GeneratedMentorDiscoveryRequest } from "@/lib/api/generated";
import { Sdk } from "@/lib/api/generated";
import { client } from "@/lib/api/generated/client.gen";
import {
  mentorDiscoveryResponseSchema,
  type MentorDiscoveryResponse,
} from "@/features/discovery/contracts";
import { parseApiData } from "@/lib/api/result";

client.setConfig({ baseUrl: "/backend" });
const sdk = new Sdk({ client });

export async function discoverOpenAlexMentors({
  candidateLimit = 12,
  paperLimit,
  query,
  signal,
}: {
  candidateLimit?: number;
  paperLimit: number;
  query: string;
  signal?: AbortSignal;
}): Promise<MentorDiscoveryResponse> {
  const body = {
    candidateLimit,
    paperLimit,
    query,
  } satisfies GeneratedMentorDiscoveryRequest;
  const result = await sdk.discoverMentorsApiV1DiscoveryMentorsPost({
    body,
    signal,
  });
  return parseApiData(result, mentorDiscoveryResponseSchema);
}
