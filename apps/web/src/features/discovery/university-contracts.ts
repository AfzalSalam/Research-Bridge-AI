import { z } from "zod";

export const universityFormSchema = z.object({
  query: z.string().trim().min(3, "Enter a specific research topic.").max(300),
  target: z.enum(["10", "20", "30"]),
  region: z.enum(["both", "india", "international"]),
});
export type UniversityForm = z.infer<typeof universityFormSchema>;
const sourceUrl = z.string().url().refine((value) => value.startsWith("https://"));
const paperSchema = z.object({
  id: z.string(), university: z.string(), title: z.string().nullable(),
  citation: z.string(), doi: z.string().nullable(), publicationUrl: sourceUrl,
  sourceUrl, checkedAt: z.string().datetime(), matchedTerms: z.array(z.string()),
});
export const programSchema = z.object({
  university: z.string(), name: z.string(), sourceUrl, checkedAt: z.string().datetime(),
  status: z.enum(["rolling", "open", "closed", "not-confirmed"]),
  deadline: z.string().nullable(), statusEvidence: z.string().nullable(),
  workMode: z.enum(["remote", "on-site", "hybrid", "not-specified"]),
  workModeEvidence: z.string().nullable(), eligibilityEvidence: z.string().nullable(),
  applicationNote: z.string(),
});
export const scanSnapshotSchema = z.object({
  state: z.enum(["scanning", "complete", "partial", "empty", "error"]),
  query: z.string(), target: z.number(), papers: z.array(paperSchema),
  programs: z.array(programSchema), pagesAttempted: z.number(), pagesRead: z.number(),
  elapsedSeconds: z.number(), budgetSeconds: z.number(),
  currentUniversity: z.string().nullable(), stopReason: z.string().nullable(),
  warnings: z.array(z.string()),
  sources: z.array(z.object({ name: z.string(), website: sourceUrl, registryUrl: sourceUrl.nullable() })).default([]),
});
export type ScanSnapshot = z.infer<typeof scanSnapshotSchema>;
export const workModeLabels = {
  remote: "Remote", "on-site": "On-site", hybrid: "Hybrid", "not-specified": "Not specified",
};
