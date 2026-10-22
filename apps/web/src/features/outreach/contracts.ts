import { z } from "zod";

const uuid = z.string().uuid();
const httpUrl = z.string().url();

export const studentFactKeySchema = z.enum([
  "profile.name",
  "profile.program",
  "profile.institution",
  "profile.researchInterests",
  "profile.skills",
  "profile.projectTitle",
  "profile.projectSummary",
  "profile.weeklyAvailability",
]);

const selectedStudentFactSchema = z.object({
  key: studentFactKeySchema,
  label: z.string().min(1),
  value: z.string().min(1),
});

const outreachPaperEvidenceSchema = z.object({
  id: uuid,
  title: z.string().min(1),
  publicationYear: z.number().int().min(1000).max(2100),
  venue: z.string().nullable(),
  evidenceStrength: z.enum(["full-abstract", "title-only"]),
  sourceUrl: httpUrl,
  lastVerifiedAt: z.string().datetime(),
});

const claimEvidenceReferenceSchema = z.object({
  type: z.enum(["student-fact", "paper"]),
  id: z.string().min(1),
  label: z.string().min(1),
  sourceUrl: httpUrl.nullable(),
});

const draftClaimEvidenceSchema = z.object({
  claim: z.string().min(5),
  references: z.array(claimEvidenceReferenceSchema).min(1),
});

export const outreachDraftResponseSchema = z.object({
  id: uuid,
  mentorId: uuid,
  recipientDisplayName: z.string().min(1),
  recipientContact: z.string().nullable(),
  contactProvenance: z.record(z.string(),z.string()).nullable().optional(),
  recipientSourceUrl: httpUrl,
  recipientLastVerifiedAt: z.string().datetime(),
  subject: z.string().trim().min(5).max(160),
  body: z.string().trim().min(80).max(5000),
  selectedStudentFacts: z.array(selectedStudentFactSchema).min(1),
  selectedPapers: z.array(outreachPaperEvidenceSchema).min(1).max(2),
  claimEvidence: z.array(draftClaimEvidenceSchema).min(1),
  uncertaintyWarnings: z.array(z.string().min(1)).min(1),
  evidenceMapStatus: z.enum([
    "verified-generated",
    "manual-edit-needs-review",
  ]),
  generation: z.object({
    mode: z.enum(["deterministic", "llm"]),
    provider: z.string().nullable(),
    model: z.string().nullable(),
    promptVersion: z.string().nullable(),
    templateVersion: z.string().min(1),
    fallbackReason: z
      .enum([
        "deterministic-requested",
        "provider-not-configured",
        "provider-unavailable",
        "provider-refused",
        "invalid-provider-output",
        "grounding-check-failed",
      ])
      .nullable(),
  }),
  draftVersion: z.number().int().min(1),
  revisions: z
    .array(
      z.object({
        version: z.number().int().min(1),
        evidenceMapStatus: z.enum([
          "verified-generated",
          "manual-edit-needs-review",
        ]),
        createdAt: z.string().datetime(),
      }),
    )
    .min(1),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
  canSend: z.literal(false),
});

export type OutreachDraftResponse = z.infer<typeof outreachDraftResponseSchema>;
