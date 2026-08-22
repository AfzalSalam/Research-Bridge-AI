import { z } from "zod";

export const applicationStatusSchema = z.enum([
  "saved",
  "drafting",
  "ready-for-review",
  "applied",
  "interviewing",
  "closed",
]);

const dateSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const dateTimeSchema = z.string().datetime({ offset: true });

export const applicationResponseSchema = z.object({
  id: z.string().uuid(),
  opportunityId: z.string().uuid(),
  targetLabel: z.string().min(1),
  sourceUrl: z.url(),
  status: applicationStatusSchema,
  notes: z.string().max(1000),
  followUpDate: dateSchema.nullable(),
  version: z.number().int().positive(),
  createdAt: dateTimeSchema,
  updatedAt: dateTimeSchema,
  events: z.array(
    z.object({
      sequence: z.number().int().positive(),
      fromStatus: applicationStatusSchema.nullable(),
      toStatus: applicationStatusSchema,
      note: z.string().nullable(),
      occurredAt: dateTimeSchema,
    }),
  ),
  allowedNextStatuses: z.array(applicationStatusSchema),
  externalSubmissionPerformed: z.literal(false).optional().default(false),
});

export const applicationListResponseSchema = z.object({
  items: z.array(applicationResponseSchema),
});

export const applicationTrackerFormSchema = z.object({
  status: applicationStatusSchema,
  notes: z.string().trim().max(1000, "Keep notes below 1,000 characters."),
  followUpDate: z
    .string()
    .refine((value) => value === "" || /^\d{4}-\d{2}-\d{2}$/.test(value), {
      message: "Choose a valid follow-up date.",
    }),
});

export type ApplicationStatus = z.infer<typeof applicationStatusSchema>;
export type ApplicationResponse = z.infer<typeof applicationResponseSchema>;
export type ApplicationTrackerForm = z.infer<
  typeof applicationTrackerFormSchema
>;
