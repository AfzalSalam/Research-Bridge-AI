"use client";
import { PassageSearch } from "./passage-search";
import { useEffect, useId } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { cancelDocumentIndex, readIndexStatus, startDocumentIndex } from "@/lib/api/documents";

const schema = z.object({ accepted: z.boolean().refine(value => value, "Please review and accept before continuing.") });
const messages = {
 not_started: "This paper has not been prepared for semantic search.",
 queued: "Waiting for the indexing worker. You can keep reading.",
 processing: "Preparing this paper for semantic search. You can keep reading.",
 completed: "Paper preparation is complete. Search by meaning below; generated answers are still coming later.",
 failed: "Preparation could not finish. Your paper and keyword search are still available.",
 cancelled: "Preparation was cancelled. Your paper and keyword search are still available.",
};
export function DocumentIndexing({ id, onPage }: { id: string; onPage?: (page: number) => void }) {
 const checkboxId = useId();
 const cache = useQueryClient();
 const query = useQuery({ queryKey: ["document-index", id], queryFn: () => readIndexStatus(id), refetchInterval: current => current.state.data && ["queued", "processing"].includes(current.state.data.status) ? 3000 : false });
 const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { accepted: false } });
 const version = query.data?.disclosure_version;
 const reset = form.reset;
 useEffect(() => { reset({ accepted: false }); }, [version, reset]);
 const refresh = () => cache.invalidateQueries({ queryKey: ["document-index", id] });
 const start = useMutation({ mutationFn: (version: string) => startDocumentIndex(id, version), onSuccess: refresh });
 const cancel = useMutation({ mutationFn: () => cancelDocumentIndex(id), onSuccess: refresh });
 return <section aria-label="Prepare paper for semantic search" className="space-y-3 border-t border-border pt-4">
  <h3 className="font-medium">Prepare for semantic search</h3>
  {query.isPending && <p role="status">Checking paper preparation...</p>}
  {query.error && <div role="alert">Could not check preparation. <Button variant="outline" onClick={() => query.refetch()}>Retry status</Button></div>}
  {query.data && <>
   <p role="status">{messages[query.data.status]}</p>
   {query.data.enabled && query.data.status === "completed" && onPage && <PassageSearch key={query.data.query_disclosure_version} id={id} onPage={onPage} semantic provider={query.data.provider} disclosureVersion={query.data.query_disclosure_version}/>}
   {!query.data.enabled && <p>Semantic indexing is not enabled yet. Keyword passage search remains available.</p>}
   {query.data.reason === "provider_changed" && <p>The search provider changed. Review the new disclosure to prepare this paper again.</p>}
   {query.data.reason === "daily_quota" && <p>Your daily AI budget has been reserved. Preparation will retry after the next UTC reset.</p>}
   {query.data.reason === "document_exceeds_quota" && <p>This paper is too large for the daily AI budget. Try a shorter paper.</p>}
   {query.data.enabled && query.data.status === "not_started" && <form key={query.data.disclosure_version} className="space-y-3" onSubmit={form.handleSubmit(() => { if (query.data) start.mutate(query.data.disclosure_version); })}>
    <p className="text-sm text-muted-foreground">This sends extracted text from this paper to {query.data.provider} to create embeddings for semantic search. Embeddings and source references are saved privately in your account. Your CV and Gmail messages are not included. This uses your daily AI budget.</p>
    {query.data.provider === "Google Gemini" && <p className="text-sm">Google may use free-tier submissions to improve its products. Use public papers; do not submit confidential research.</p>}
    <div className="flex items-start gap-2"><input id={checkboxId} type="checkbox" disabled={start.isPending} {...form.register("accepted")}/><label htmlFor={checkboxId}>I agree to send this paper&apos;s extracted text to {query.data.provider} for indexing.</label></div>
    {form.formState.errors.accepted && <p role="alert">{form.formState.errors.accepted.message}</p>}
    <Button disabled={start.isPending}>{start.isPending ? "Queueing..." : "Prepare this paper"}</Button>
   </form>}
   {["queued", "processing"].includes(query.data.status) && <><Button variant="outline" disabled={cancel.isPending} onClick={() => cancel.mutate()}>Cancel preparation</Button><p className="text-sm text-muted-foreground">Cancellation stops future batches. Text already sent in an ongoing request cannot be recalled; reserved usage remains counted.</p></>}
  </>}
  {start.error && <p role="alert">{start.error.message}</p>}
  {cancel.error && <p role="alert">{cancel.error.message}</p>}
 </section>;
}
