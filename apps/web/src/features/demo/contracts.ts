import { z } from "zod";

const shortText = z.string().trim().min(2).max(120);
const sourceUrl = z.string().url().startsWith("https://example.org/");

function hasUniqueTerms(values: string[]): boolean {
  const normalized = values.map((value) => value.trim().toLocaleLowerCase());
  return normalized.length === new Set(normalized).size;
}

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
      `Remove duplicate ${label}.`,
    );
}

export const studentProfileSchema = z.object({
  id: z.literal("demo-student"),
  name: z.string().trim().min(2, "Enter at least 2 characters.").max(60),
  program: shortText,
  institution: shortText,
  graduationYear: z
    .string()
    .regex(/^20\d{2}$/, "Use a four-digit year, for example 2027."),
  researchInterests: z
    .array(shortText)
    .min(1)
    .max(6)
    .refine(hasUniqueTerms, "Research interests must be unique."),
  skills: z
    .array(shortText)
    .min(1)
    .max(8)
    .refine(hasUniqueTerms, "Skills must be unique."),
  projectTitle: shortText,
  projectSummary: z.string().trim().min(40).max(500),
  weeklyAvailability: z.enum(["5-10 hours", "10-15 hours", "15+ hours"]),
});

export const profileFormSchema = z.object({
  name: studentProfileSchema.shape.name,
  program: studentProfileSchema.shape.program,
  institution: studentProfileSchema.shape.institution,
  graduationYear: studentProfileSchema.shape.graduationYear,
  researchInterests: commaList(6, "research interests"),
  skills: commaList(8, "skills"),
  projectTitle: studentProfileSchema.shape.projectTitle,
  projectSummary: studentProfileSchema.shape.projectSummary,
  weeklyAvailability: studentProfileSchema.shape.weeklyAvailability,
});

export const paperEvidenceSchema = z.object({
  id: z.string().min(1),
  title: shortText,
  authors: z.array(shortText).min(1),
  year: z.number().int().min(2000).max(2100),
  venue: shortText,
  summary: z.string().trim().min(20).max(600),
  topics: z.array(shortText).min(1),
  evidenceStrength: z.enum(["full-abstract", "title-only"]),
  sourceUrl,
});

export const mentorCandidateSchema = z.object({
  id: z.string().min(1),
  name: shortText,
  role: shortText,
  department: shortText,
  institution: shortText,
  location: shortText,
  researchThemes: z.array(shortText).min(1),
  fitRationale: z.array(z.string().trim().min(10).max(240)).min(1),
  identityNote: z.string().trim().min(10).max(240),
  sourceUrl,
  papers: z.array(paperEvidenceSchema).min(1),
});

export const discoveryScenarioSchema = z.enum([
  "complete",
  "partial",
  "empty",
  "error",
]);

export const discoveryStateSchema = z.object({
  query: z.string().max(180),
  scenario: discoveryScenarioSchema,
  status: z.enum(["idle", "searching", "complete", "partial", "empty", "error"]),
  stage: z.number().int().min(0).max(3),
  mentorIds: z.array(z.string()),
  errorMessage: z.string().nullable(),
});

export const outreachDraftSchema = z.object({
  id: z.string().min(1),
  mentorId: z.string().min(1),
  paperIds: z.array(z.string()).min(1).max(2),
  subject: z.string().trim().min(5).max(160),
  body: z.string().trim().min(80).max(5000),
  selectedStudentFacts: z.array(z.string().min(1)).min(1),
  claimEvidence: z
    .array(
      z.object({
        claim: z.string().min(1),
        evidenceIds: z.array(z.string().min(1)).min(1),
      }),
    )
    .min(1),
  uncertaintyWarnings: z.array(z.string().min(1)).min(1),
  generatedAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
  mode: z.literal("deterministic-demo"),
  templateVersion: z.literal("phase-04.v1"),
  draftVersion: z.literal(1),
  evidenceLinks: z.array(sourceUrl).min(2),
});

export const opportunitySchema = z.object({
  id: z.string().min(1),
  title: shortText,
  organisation: shortText,
  location: shortText,
  mode: z.enum(["On-site", "Hybrid", "Remote", "Unknown"]),
  funding: z.enum(["Funded", "Unfunded", "Unknown"]),
  availability: z.enum(["Open", "Closed", "Unknown"]),
  deadline: z.string().nullable(),
  description: z.string().trim().min(20).max(500),
  topics: z.array(shortText).min(1),
  sourceUrl,
  lastVerifiedAt: z.string().datetime(),
});

export const applicationStatusSchema = z.enum([
  "Saved",
  "Drafting",
  "Ready for review",
  "Applied",
  "Interviewing",
  "Closed",
]);

export const applicationHistorySchema = z.object({
  status: applicationStatusSchema,
  changedAt: z.string().datetime(),
});

export const applicationSchema = z.object({
  id: z.string().min(1),
  targetType: z.enum(["mentor", "opportunity"]),
  targetId: z.string().min(1),
  targetLabel: shortText,
  sourceUrl,
  status: applicationStatusSchema,
  notes: z.string().max(1000),
  followUpDate: z.string().nullable(),
  updatedAt: z.string().datetime(),
  history: z.array(applicationHistorySchema).min(1),
});

export const demoStateSchema = z.object({
  schemaVersion: z.literal(1),
  profile: studentProfileSchema,
  discovery: discoveryStateSchema,
  selectedMentorId: z.string().nullable(),
  selectedPaperIds: z.record(z.string(), z.array(z.string())),
  drafts: z.array(outreachDraftSchema),
  savedOpportunityIds: z.array(z.string()),
  applications: z.array(applicationSchema),
});

export const demoBootstrapSchema = z.object({
  schemaVersion: z.literal(1),
  mode: z.literal("fictional-demo"),
  defaultQuery: z.string().trim().min(12).max(180),
  profile: studentProfileSchema,
  mentors: z.array(mentorCandidateSchema).min(1),
  opportunities: z.array(opportunitySchema).min(1),
});

export const discoveryResponseSchema = z.object({
  status: z.enum(["complete", "partial", "empty"]),
  mentorIds: z.array(z.string().min(1)),
  sourceWarning: z.string().min(1).nullable(),
});

export const apiErrorResponseSchema = z.object({
  error: z.object({
    code: z.string().min(1),
    message: z.string().min(1),
    requestId: z.string().min(1),
    details: z.array(
      z.object({
        field: z.string(),
        message: z.string().min(1),
        type: z.string().min(1),
      }),
    ),
  }),
});

export type Application = z.infer<typeof applicationSchema>;
export type ApplicationStatus = z.infer<typeof applicationStatusSchema>;
export type ApiErrorResponse = z.infer<typeof apiErrorResponseSchema>;
export type DemoBootstrap = z.infer<typeof demoBootstrapSchema>;
export type DemoState = z.infer<typeof demoStateSchema>;
export type DiscoveryScenario = z.infer<typeof discoveryScenarioSchema>;
export type DiscoveryResponse = z.infer<typeof discoveryResponseSchema>;
export type MentorCandidate = z.infer<typeof mentorCandidateSchema>;
export type Opportunity = z.infer<typeof opportunitySchema>;
export type OutreachDraft = z.infer<typeof outreachDraftSchema>;
export type PaperEvidence = z.infer<typeof paperEvidenceSchema>;
export type ProfileFormValues = z.infer<typeof profileFormSchema>;
export type StudentProfile = z.infer<typeof studentProfileSchema>;
