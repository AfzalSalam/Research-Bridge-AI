import { contactResponseSchema, type ContactRequest } from "@/features/mentors/contact-contracts";
import { Sdk, type ContactLookupRequest } from "@/lib/api/generated";
import { client } from "@/lib/api/generated/client.gen";
import { parseApiData } from "@/lib/api/result";

const sdk = new Sdk({ client });
export async function findPublicEmail(authorId: string, body: ContactRequest, signal: AbortSignal) {
  const result = await sdk.lookupPublicEmailApiV1AuthorsAuthorIdPublicEmailPost({
    path: { author_id: authorId }, body: body satisfies ContactLookupRequest, signal,
  });
  return parseApiData(result, contactResponseSchema);
}
