import { z } from "zod";
import { researchRequest } from "./research";
export const documentSchema = z.object({ id: z.string().uuid(), filename: z.string(), status: z.enum(["uploading", "quarantined", "processing", "ready", "unsupported", "rejected", "failed"]), reason: z.string().nullable(), warnings: z.array(z.string()) });
export type PaperDocument = z.infer<typeof documentSchema>;
export const documentsSchema = z.object({ uploads_enabled: z.boolean(), documents: z.array(documentSchema) });
export const listDocuments = (paperId: string) => researchRequest(`/documents/paper/${paperId}`, documentsSchema);
export const readDocumentPages = (id: string) => researchRequest(`/documents/${id}/pages`, z.array(z.object({ number: z.number().int(), text: z.string() })));
export const deleteDocument = (id: string) => researchRequest(`/documents/${id}`, z.null(), { method: "DELETE" });
export const uploadDocument = (paperId: string, file: File) => researchRequest(`/documents/paper/${paperId}?filename=${encodeURIComponent(file.name)}`, z.object({ id: z.string().uuid() }), { method: "POST", headers: { "Content-Type": "application/pdf" }, body: file });


export async function readOriginalPdf(id: string, signal: AbortSignal): Promise<Blob> {
 const { getAccessToken } = await import("./setup");
 const token = await getAccessToken();
 if (!token) throw new Error("Sign in to read your PDF.");
 const response = await fetch(`/backend/api/v1/documents/${encodeURIComponent(id)}/file`, {
  signal, cache: "no-store", headers: { Authorization: `Bearer ${token}` },
 });
 if (!response.ok) throw new Error(response.status === 409
  ? "This PDF is not ready or no longer matches the scanned file."
  : response.status === 404 ? "This PDF is no longer available in your account."
  : "Could not load the PDF. Please try again.");
 if (response.headers.get("content-type")?.split(";")[0] !== "application/pdf")
  throw new Error("The server did not return a PDF.");
 const blob = await response.blob();
 if (blob.size === 0 || blob.size > 20 * 1024 * 1024) throw new Error("The PDF has an invalid size.");
 return blob;
}


export const passagesSchema = z.object({
 document_id: z.string().uuid(), status: z.enum(["matches", "no_matches"]),
 engine: z.enum(["postgresql_fts", "lexical_fallback"]), notice: z.string(),
 passages: z.array(z.object({ page: z.number().int().min(1).max(100),
  start: z.number().int().min(0), end: z.number().int().min(0), text: z.string() })),
});
export const searchDocumentPassages = (id: string, query: string) =>
 researchRequest(`/documents/${id}/passages`, passagesSchema,
  { method: "POST", body: JSON.stringify({ query, limit: 5 }) });


export const indexStatusSchema = z.object({
 enabled: z.boolean(), status: z.enum(["not_started", "queued", "processing", "completed", "failed", "cancelled"]),
 reason: z.string().nullable(), retry_at: z.string().nullable(), disclosure_version: z.string(),
 reserved_today: z.number(), daily_limit: z.number(),
 provider: z.enum(["OpenAI", "Google Gemini"]).default("OpenAI"),
 query_disclosure_version: z.string().default("paper-query-embeddings-v1"),
});
export const readIndexStatus = (id: string) => researchRequest(`/documents/${id}/index`, indexStatusSchema);
export const startDocumentIndex = (id: string, version: string) => researchRequest(`/documents/${id}/index`, z.object({ id: z.string().uuid() }), { method: "POST", body: JSON.stringify({ accepted: true, disclosure_version: version }) });
export const cancelDocumentIndex = (id: string) => researchRequest(`/documents/${id}/index`, z.null(), { method: "DELETE" });


export const searchSemanticPassages = (id: string, query: string, version = "paper-query-embeddings-v1") =>
 researchRequest(`/documents/${id}/semantic-passages`, z.object({
  document_id: z.string().uuid(), notice: z.string(), passages: passagesSchema.shape.passages,
 }), { method: "POST", body: JSON.stringify({ query, limit: 5, accepted: true,
  disclosure_version: version }) });


export const answerStatusSchema = z.object({
 enabled: z.boolean(), provider: z.string(), model: z.string(),
 disclosure_version: z.string(), disclosure: z.string(),
 reserved_calls_today: z.number().int().nonnegative(), daily_call_limit: z.number().int().positive(),
 calls_reserved_per_question: z.number().int().positive(),
});
export type AnswerStatus = z.infer<typeof answerStatusSchema>;
export const answerResultSchema = z.object({
 status: z.enum(["answer", "insufficient_evidence", "unavailable"]), reason: z.string(), notice: z.string(),
 source_scope: z.literal("retrieved_full_text_excerpts"),
 claims: z.array(z.object({ text: z.string(), citations: z.array(z.object({
  page: z.number().int().min(1).max(100), start: z.number().int().nonnegative(),
  end: z.number().int().positive(), quote: z.string(),
 })) })),
});
export const readAnswerStatus = (id: string) => researchRequest(`/documents/${id}/answers`, answerStatusSchema);
export const askDocument = (id: string, question: string, version: string, requestId: string) =>
 researchRequest(`/documents/${id}/answers`, answerResultSchema, { method: "POST", body: JSON.stringify({
  question, accepted: true, disclosure_version: version, request_id: requestId,
 }) });

export const readingHistorySchema = z.array(z.object({
 id: z.string().uuid(), question: z.string(), result: answerResultSchema,
 model: z.string(), created_at: z.string(),
}));
export const readReadingHistory = (id: string) => researchRequest(`/documents/${id}/reading-history`, readingHistorySchema);
