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

function commaList(maxItems: number, label: string) {
  return z
    .string()
    .trim()
    .min(2, `Add at least one ${label}.`)
    .max(240)
    .refine(
      (value) => value.split(",").filter((item) => item.trim()).length <= maxItems,
      `Add no more than ${maxItems} ${label}.`,
    )
    .refine(
      (value) =>
        value
          .split(",")
          .filter((item) => item.trim())
          .every((item) => item.trim().length >= 2),
      `Each ${label.replace(/s$/, "")} must contain at least 2 characters.`,
    )
    .refine(
      (value) => hasUniqueTerms(value.split(",").filter((item) => item.trim())),
      `${label} must be unique.`,
    );
}

export const accountProfileFormSchema = z.object({
  name: accountProfileSchema.shape.name,
  program: accountProfileSchema.shape.program,
  institution: accountProfileSchema.shape.institution,
  graduationYear: accountProfileSchema.shape.graduationYear,
  researchInterests: commaList(6, "research interests"),
  skills: commaList(8, "skills"),
  projectTitle: accountProfileSchema.shape.projectTitle,
  projectSummary: accountProfileSchema.shape.projectSummary,
  weeklyAvailability: accountProfileSchema.shape.weeklyAvailability,
});

export type AccountProfileFormValues = z.infer<typeof accountProfileFormSchema>;

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
