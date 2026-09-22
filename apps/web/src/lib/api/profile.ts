import { Sdk, type AccountProfile as GeneratedAccountProfile, type AccountProfileReadResponse } from "@/lib/api/generated";
import { client } from "@/lib/api/generated/client.gen";
import { ApiError, parseApiData } from "@/lib/api/result";
import { z } from "zod";

const shortText = z.string().trim().min(2).max(120);

function hasUniqueTerms(values: string[]): boolean {
  const normalized = values.map((value) => value.trim().toLocaleLowerCase());
  return normalized.length === new Set(normalized).size;
}

export const accountProfileSchema = z.object({
  name: z.string().trim().min(2).max(60),
  program: shortText,
  institution: shortText,
  graduationYear: z.string().regex(/^20\d{2}$/),
  researchInterests: z.array(shortText).min(1).max(6).refine(hasUniqueTerms),
  skills: z.array(shortText).min(1).max(8).refine(hasUniqueTerms),
  projectTitle: shortText,
  projectSummary: z.string().trim().min(40).max(500),
  weeklyAvailability: z.enum(["5-10 hours", "10-15 hours", "15+ hours"]),
});

export const accountProfileResponseSchema = z.object({
  profile: accountProfileSchema.nullable(),
});

export type AccountProfile = z.infer<typeof accountProfileSchema>;

const sdk = new Sdk({ client });

export async function getAccountProfile(signal?: AbortSignal): Promise<AccountProfile | null> {
  const result = await sdk.readAccountProfileApiV1ProfileGet({ signal });
  const response = parseApiData(result, accountProfileResponseSchema);
  return response.profile;
}

export async function updateAccountProfile(
  profile: AccountProfile,
  signal?: AbortSignal,
): Promise<AccountProfile> {
  const body = profile satisfies GeneratedAccountProfile;
  const result = await sdk.updateAccountProfileApiV1ProfilePut({ body, signal });
  return parseApiData(result, accountProfileSchema);
}
