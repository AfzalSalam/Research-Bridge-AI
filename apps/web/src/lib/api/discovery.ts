import type { PaperDiscoveryRequest as GeneratedPaperDiscoveryRequest } from "@/lib/api/generated";
import { Sdk } from "@/lib/api/generated";
import { client } from "@/lib/api/generated/client.gen";
import {
  paperDiscoveryResponseSchema,
  type PaperDiscoveryResponse,
} from "@/features/discovery/contracts";
import { parseApiData } from "@/lib/api/result";

client.setConfig({ baseUrl: "/backend" });
const sdk = new Sdk({ client });

export async function discoverOpenAlexPapers({
  limit,
  query,
  signal,
}: {
  limit: number;
  query: string;
  signal?: AbortSignal;
}): Promise<PaperDiscoveryResponse> {
  const body = { query, limit } satisfies GeneratedPaperDiscoveryRequest;
  const result = await sdk.discoverPapersApiV1DiscoveryPapersPost({ body, signal });
  return parseApiData(result, paperDiscoveryResponseSchema);
}
