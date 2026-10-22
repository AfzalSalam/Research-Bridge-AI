import { z } from "zod";

const publicUrl = z.string().url().refine((value) => value.startsWith("https://"));
export const contactRequestSchema = z.object({ profileUrl: z.string().max(1800).optional(), refresh: z.boolean().optional() });
export const contactResponseSchema = z.object({
  authorId: z.string().uuid(), authorName: z.string(),
  status: z.enum(["found", "not-found", "needs-review", "unsupported", "blocked"]),
  emails: z.array(z.object({
    email: z.string().email(), sourceUrl: publicUrl,
    identityEvidence: z.array(z.string()), evidenceUrls: z.array(publicUrl),
    extraction: z.enum(["mailto", "text", "obfuscated"]), checkedAt: z.string().datetime(),
  })),
  profiles: z.array(z.object({ sourceUrl: publicUrl, reason: z.string() })),
  warnings: z.array(z.string()), checkedAt: z.string().datetime(),
  pagesChecked: z.number(), elapsedSeconds: z.number(), cacheHit: z.boolean(),
  institutionSources: z.array(publicUrl).default([]),
  lookupUrl: z.string().nullable(), verification: z.literal("official-profile-evidence-not-deliverability"),
});
export type ContactRequest = z.infer<typeof contactRequestSchema>;
export type ContactResponse = z.infer<typeof contactResponseSchema>;
