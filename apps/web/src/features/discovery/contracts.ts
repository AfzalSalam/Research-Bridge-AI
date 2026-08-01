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

const paperInstitutionSchema = z.object({
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
