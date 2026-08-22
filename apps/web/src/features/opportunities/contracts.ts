import { z } from "zod";

const dateSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const dateTimeSchema = z.string().datetime({ offset: true });

export const opportunitySearchFormSchema = z.object({
  query: z
    .string()
    .trim()
    .min(2, "Describe a research topic using at least 2 characters.")
    .max(160, "Keep the topic below 160 characters."),
  countryCode: z
    .string()
    .trim()
    .max(2, "Use a two-letter country code.")
    .refine((value) => value === "" || /^[A-Za-z]{2}$/.test(value), {
      message: "Use a two-letter country code such as IN or US.",
    })
    .transform((value) => value.toUpperCase() || null),
  workMode: z
    .enum(["", "on-site", "hybrid", "remote", "unclear"])
    .transform((value) => value || null),
  funding: z
    .enum(["", "funded", "unfunded", "unclear"])
    .transform((value) => value || null),
  includeExpired: z.boolean(),
  limit: z.coerce.number().int().min(1).max(30),
});

export type OpportunitySearchFormInput = z.input<
  typeof opportunitySearchFormSchema
>;
export type OpportunitySearchForm = z.output<typeof opportunitySearchFormSchema>;

export const opportunityExtractionEvidenceSchema = z.object({
  field: z.string().min(1),
  value: z.string().min(1),
});

export const opportunityResultSchema = z.object({
  id: z.string().uuid(),
  sourceName: z.string().min(1),
  sourceKind: z.literal("official-ats"),
  sourceRecordId: z.string().min(1),
  evidenceConfidence: z.literal("high"),
  opportunityType: z.enum([
    "internship",
    "studentship",
    "fellowship",
    "research-assistantship",
  ]),
  title: z.string().min(1),
  organisation: z.string().min(1),
  descriptionExcerpt: z.string().min(1),
  researchFields: z.array(z.string().min(1)),
  duration: z.string().nullable(),
  eligibility: z.string().nullable(),
  countryCode: z.string().length(2).nullable(),
  location: z.string().nullable(),
  workMode: z.enum(["on-site", "hybrid", "remote", "unclear"]),
  funding: z.enum(["funded", "unfunded", "unclear"]),
  availability: z.enum(["open", "closed", "unclear"]),
  deadline: dateSchema.nullable(),
  sourceUrl: z.url(),
  applicationUrl: z.url(),
  sourceUpdatedAt: dateTimeSchema,
  lastVerifiedAt: dateTimeSchema,
  isStale: z.boolean(),
  isExpired: z.boolean(),
  extractionEvidence: z.array(opportunityExtractionEvidenceSchema),
  inclusionSignal: z.string().min(1),
  isSaved: z.boolean(),
  applicationId: z.string().uuid().nullable(),
});

export const opportunitySearchResponseSchema = z.object({
  query: z.string().min(1),
  results: z.array(opportunityResultSchema),
  sources: z.array(
    z.object({
      key: z.string().min(1),
      organisation: z.string().min(1),
      status: z.enum(["success", "error"]),
      acceptedCount: z.number().int().nonnegative(),
      invalidCount: z.number().int().nonnegative(),
      errorCode: z.string().nullable().optional(),
      retryable: z.boolean().optional(),
    }),
  ),
  partialFailure: z.boolean(),
  policyVersion: z.string().min(1),
  retrievedAt: dateTimeSchema,
  rankingApplied: z.literal(false).optional().default(false),
});

export const savedOpportunitySchema = z.object({
  savedAt: dateTimeSchema,
  opportunity: opportunityResultSchema,
});

export const savedOpportunityListResponseSchema = z.object({
  items: z.array(savedOpportunitySchema),
});

export type OpportunityResult = z.infer<typeof opportunityResultSchema>;
export type OpportunitySearchResponse = z.infer<
  typeof opportunitySearchResponseSchema
>;
export type SavedOpportunity = z.infer<typeof savedOpportunitySchema>;
