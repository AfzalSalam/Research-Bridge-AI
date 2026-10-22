"use client";

import { useId } from "react";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { searchDocumentPassages, searchSemanticPassages } from "@/lib/api/documents";

const schema = z.object({ accepted: z.boolean().optional(), query: z.string().trim().min(1, "Enter a topic or keyword.").max(500, "Use 500 characters or fewer.") });
export function PassageSearch({ id, onPage, semantic = false, provider = "OpenAI", disclosureVersion = "paper-query-embeddings-v1" }: { id: string; onPage: (page: number) => void; semantic?: boolean; provider?: string; disclosureVersion?: string }) {
 const inputId = useId();
 const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { accepted: false } });
 const search = useMutation({ mutationFn: (query: string) => (semantic ? searchSemanticPassages(id, query, disclosureVersion) : searchDocumentPassages(id, query)), gcTime: 0 });
 return <section aria-label={semantic ? "Semantic search within this paper" : "Search within this paper"} className="space-y-3 border-t border-border pt-4">
  <h3 className="font-medium">{semantic ? "Search by meaning" : "Find passages in this paper"}</h3>
  <p className="text-sm text-muted-foreground">{semantic ? "Ask a question or describe a topic to find related passages. These are source excerpts, not AI-generated answers." : "Search using words from the paper, such as a method or dataset. These are matching excerpts, not AI-generated answers."}</p>
  <form className="space-y-2" onSubmit={form.handleSubmit(values => {
    if (semantic && !values.accepted) { form.setError("accepted", { message: "Review and accept query sharing before searching." }); return; }
    search.mutate(values.query);
   })}>
   <label className="block" htmlFor={inputId}>{semantic ? "Question or topic" : "Topic or keywords"}</label>
   <input id={inputId} maxLength={500} disabled={search.isPending} className="w-full rounded border border-border bg-background p-2" {...form.register("query")} />
   {form.formState.errors.query && <p role="alert">{form.formState.errors.query.message}</p>}
   {semantic && <>
    <p className="text-sm text-muted-foreground">Your question is sent to {provider} to create a search embedding and uses your daily AI budget. It is not saved by this search service. Your CV and Gmail messages are not sent.</p>
    {provider === "Google Gemini" && <p className="text-sm">Google may use free-tier submissions to improve its products. Do not include private information in questions.</p>}
    <label className="flex items-start gap-2"><input type="checkbox" disabled={search.isPending} {...form.register("accepted")}/>I agree to send my search questions to {provider} while using this form.</label>
    {form.formState.errors.accepted && <p role="alert">{form.formState.errors.accepted.message}</p>}
   </>}
   <Button disabled={search.isPending}>{search.isPending ? "Searching passages..." : semantic ? "Search by meaning" : "Find passages"}</Button>
  </form>
  {search.isPending && <p role="status">Searching the extracted paper text...</p>}
  {search.error && <p role="alert">{search.error.message} Submit the search again to retry.</p>}
  {!search.isPending && !search.error && search.data && <>
   <p className="text-sm">Results for: {search.variables}</p>
   {search.data.passages.length === 0 ? <p role="status">No matching passages found. Try different keywords. This does not prove the paper has no relevant information.</p> : <>
    <p role="status">Found {search.data.passages.length} matching passages. Check each source page before drawing conclusions.</p>
    <ol className="space-y-3">{search.data.passages.map(passage => <li key={`${passage.page}-${passage.start}`} className="space-y-2 rounded border border-border p-3">
     <blockquote className="whitespace-pre-wrap break-words">{passage.text}</blockquote>
     <Button variant="outline" onClick={() => onPage(passage.page)}>Read page {passage.page}</Button>
    </li>)}</ol>
   </>}
  </>}
 </section>;
}
