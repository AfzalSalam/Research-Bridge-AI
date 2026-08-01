import { z } from "zod";

const openAlexUrl = z.string().url().startsWith("https://openalex.org");
const uuid = z.string().uuid();

export const livePaperSearchFormSchema = z.object({
  query: z
    .string()
    .trim()
    .min(3, "Enter a topic, DOI, or OpenAlex Work ID.")
    .max(300),
  limit: z.coerce.number().int().min(1).max(25),
});

export const paperInstitutionSchema = z.object({
  id: uuid,
  openalexId: z.string().nullable(),
  rorId: z.string().nullable(),
  displayName: z.string().min(1),
  countryCode: z.string().length(2).nullable(),
  city: z.string().min(1).nullable(),
  sourceUrl: openAlexUrl,
});

const paperAuthorSchema = z.object({
  id: uuid,
  openalexId: z.string().nullable(),
  orcid: z.string().nullable(),
  displayName: z.string().min(1),
  isCorresponding: z.boolean().nullable(),
  sourceUrl: openAlexUrl,
  institutions: z.array(paperInstitutionSchema),
});

const paperTopicSchema = z.object({
  id: uuid,
  openalexId: z.string().nullable(),
  displayName: z.string().min(1),
  score: z.number().min(0).max(1).nullable(),
});

const discoveredPaperSchema = z.object({
  id: uuid,
  openalexId: z.string().regex(/^W\d+$/),
  doi: z.string().nullable(),
  title: z.string().min(1),
  publicationYear: z.number().int().min(1000).max(2100),
  publicationDate: z.string().nullable(),
  workType: z.string().nullable(),
  language: z.string().nullable(),
  venue: z.string().nullable(),
  abstractExcerpt: z.string().nullable(),
  evidenceStrength: z.enum(["full-abstract", "title-only"]),
  sourceUrl: openAlexUrl,
  lastVerifiedAt: z.string().datetime(),
  authors: z.array(paperAuthorSchema),
  topics: z.array(paperTopicSchema),
});

export const paperDiscoveryResponseSchema = z.object({
  status: z.enum(["complete", "partial", "empty"]),
  query: z.string().min(1),
  queryKind: z.enum(["text", "doi", "openalex-id"]),
  ordering: z.literal("openalex-provider"),
  totalProviderResults: z.number().int().min(0).nullable(),
  returnedCount: z.number().int().min(0),
  skippedCount: z.number().int().min(0),
  warnings: z.array(z.string().min(1)),
  source: z.object({
    name: z.literal("OpenAlex"),
    sourceUrl: openAlexUrl,
    retrievedAt: z.string().datetime(),
    accessMode: z.enum(["api-key", "limited-anonymous"]),
    cacheStatus: z.enum(["hit", "miss"]),
    rateLimitRemaining: z.number().int().min(0).nullable(),
    rateLimitResetSeconds: z.number().int().min(0).nullable(),
  }),
  papers: z.array(discoveredPaperSchema),
});

export type DiscoveredPaper = z.infer<typeof discoveredPaperSchema>;
export type LivePaperSearchForm = z.infer<typeof livePaperSearchFormSchema>;
export type LivePaperSearchFormInput = z.input<typeof livePaperSearchFormSchema>;
export type PaperDiscoveryResponse = z.infer<typeof paperDiscoveryResponseSchema>;

const policyFeatureSchema = z.enum([
  "query-evidence",
  "profile-alignment",
  "supporting-depth",
  "recent-activity",
  "evidence-completeness",
]);

export const liveMentorSearchFormSchema = z.object({
  query: z
    .string()
    .trim()
    .min(3, "Enter a topic, DOI, or OpenAlex Work ID.")
    .max(300),
  paperLimit: z.coerce.number().int().min(1).max(25),
});

const mentorFeatureContributionSchema = z.object({
  feature: policyFeatureSchema,
  label: z.string().min(1),
  value: z.number().min(0).max(1),
  weight: z.number().min(0).max(1),
  contribution: z.number().min(0).max(1),
  explanation: z.string().min(10),
  matchedTerms: z.array(z.string().min(1)),
  evidencePaperIds: z.array(uuid),
});

const mentorSupportingPaperSchema = z.object({
  id: uuid,
  openalexId: z.string().regex(/^W\d+$/),
  doi: z.string().nullable(),
  title: z.string().min(1),
  publicationYear: z.number().int().min(1000).max(2100),
  publicationDate: z.string().nullable(),
  workType: z.string().nullable(),
  language: z.string().nullable(),
  venue: z.string().nullable(),
  abstractExcerpt: z.string().nullable(),
  evidenceStrength: z.enum(["full-abstract", "title-only"]),
  sourceUrl: openAlexUrl,
  lastVerifiedAt: z.string().datetime(),
  authorship: z.object({
    position: z.number().int().min(1),
    isCorresponding: z.boolean().nullable(),
    affiliationsAtPublication: z.array(paperInstitutionSchema),
  }),
  topics: z.array(paperTopicSchema),
});

const mentorCandidateSchema = z.object({
  id: uuid,
  displayName: z.string().min(1),
  openalexId: z.string().nullable(),
  orcid: z.string().nullable(),
  sourceUrl: openAlexUrl,
  lastVerifiedAt: z.string().datetime(),
  academicTitle: z.null(),
  currentInstitution: z.null(),
  availability: z.literal("unknown"),
  researchThemes: z.array(z.string().min(1)),
  supportingPaperCount: z.number().int().min(1),
  supportingPapers: z.array(mentorSupportingPaperSchema).min(1),
  relevanceBand: z.enum(["strong", "promising", "exploratory"]),
  evidenceConfidence: z.enum(["high", "moderate", "limited"]),
  evidenceCompleteness: z.number().min(0).max(1),
  contributions: z.array(mentorFeatureContributionSchema),
  warnings: z.array(z.string().min(1)),
});

export const mentorDiscoveryResponseSchema = z.object({
  status: z.enum(["complete", "partial", "empty"]),
  query: z.string().min(1),
  queryKind: z.enum(["text", "doi", "openalex-id"]),
  ordering: z.literal("deterministic-evidence-policy"),
  profileMode: z.literal("saved-or-fictional-fallback"),
  profileInputs: z.object({
    researchInterests: z.array(z.string().min(1)),
    skills: z.array(z.string().min(1)),
    projectTitle: z.string().min(1),
  }),
  policy: z.object({
    version: z.literal("placement-relevance-v1"),
    ordering: z.literal("deterministic-evidence-policy"),
    weights: z.array(
      z.object({
        feature: policyFeatureSchema,
        label: z.string().min(1),
        weight: z.number().min(0).max(1),
      }),
    ),
    scoreVisibility: z.literal("bands-and-contributions-only"),
  }),
  source: z.object({
    name: z.literal("OpenAlex"),
    sourceUrl: openAlexUrl,
    retrievedAt: z.string().datetime(),
    accessMode: z.enum(["api-key", "limited-anonymous"]),
    cacheStatus: z.enum(["hit", "miss"]),
    rateLimitRemaining: z.number().int().min(0).nullable(),
    rateLimitResetSeconds: z.number().int().min(0).nullable(),
  }),
  paperCount: z.number().int().min(0),
  authorAppearanceCount: z.number().int().min(0),
  derivedCandidateCount: z.number().int().min(0),
  returnedCount: z.number().int().min(0),
  warnings: z.array(z.string().min(1)),
  quality: z.object({
    authorAppearances: z.number().int().min(0),
    uniqueCandidates: z.number().int().min(0),
    duplicateCollapseRate: z.number().min(0).max(1),
    meanEvidenceCoverage: z.number().min(0).max(1),
    unsupportedClaimRate: z.number().min(0).max(1),
  }),
  timing: z.object({
    retrievalAndPersistenceMs: z.number().int().min(0),
    heuristicMs: z.number().int().min(0),
    totalMs: z.number().int().min(0),
  }),
  candidates: z.array(mentorCandidateSchema),
});

export type LiveMentorSearchForm = z.infer<typeof liveMentorSearchFormSchema>;
export type LiveMentorSearchFormInput = z.input<
  typeof liveMentorSearchFormSchema
>;
export type MentorCandidateResult = z.infer<typeof mentorCandidateSchema>;
export type MentorDiscoveryResponse = z.infer<
  typeof mentorDiscoveryResponseSchema
>;
