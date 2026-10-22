"use client";

import { useId, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { askDocument, readAnswerStatus, type AnswerStatus } from "@/lib/api/documents";
import { ReadingHistory } from "./reading-history";

const schema = z.object({ question: z.string().trim().min(1, "Enter a question.").max(500), accepted: z.boolean() });
type Props = { id: string; onPage: (page: number) => void };

export function PaperAnswers({ id, onPage }: Props) {
 const status = useQuery({ queryKey: ["paper-answer-status", id], queryFn: () => readAnswerStatus(id), retry: false });
 return <section aria-label="Ask about this paper" className="space-y-3 border-t border-border pt-4">
  <h3 className="font-medium">Ask about this paper</h3>
  {status.isPending ? <p role="status">Checking paper-answer availability…</p> : status.error ?
   <div role="alert">Could not check answer availability. <Button variant="outline" onClick={() => status.refetch()}>Check again</Button></div> :
   !status.data.enabled ? <p role="status">AI answers are not enabled yet. You can still read the paper and find passages above.</p> :
   <AnswerForm key={`${id}:${status.data.provider}:${status.data.model}:${status.data.disclosure_version}:${status.data.disclosure}`} id={id} onPage={onPage} status={status.data}/>}
  <ReadingHistory id={id} onPage={onPage}/>
 </section>;
}

function AnswerForm({ id, onPage, status }: Props & { status: AnswerStatus }) {
 const input = useId();
 const locked = useRef(false);
 const cache = useQueryClient();
 const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { question: "", accepted: false } });
 const exhausted = status.reserved_calls_today + status.calls_reserved_per_question > status.daily_call_limit;
 const result = useMutation({
  mutationFn: (question: string) => askDocument(id, question, status.disclosure_version, crypto.randomUUID()),
  retry: false, gcTime: 0,
  onSettled: () => { locked.current = false; void cache.invalidateQueries({ queryKey: ["reading-history", id] }); void cache.invalidateQueries({ queryKey: ["paper-answer-status", id] }); },
 });
 return <div className="space-y-3">
  <p className="text-sm">Answers use retrieved excerpts, not an exhaustive review of the paper. AI checks can miss mistakes; check the cited pages.</p>
  <p className="text-sm">{status.disclosure}</p>
  <p className="text-sm">{Math.max(0, Math.floor((status.daily_call_limit - status.reserved_calls_today) / status.calls_reserved_per_question))} questions remaining in today’s allowance. Failed attempts may still use allowance.</p>
  {exhausted && <p role="status">Today’s answer allowance is used. It resets at midnight UTC.</p>}
  <form className="space-y-2" onSubmit={event => { void form.handleSubmit(values => {
   if (locked.current || exhausted) return;
   if (!values.accepted) { form.setError("accepted", { message: "Review and accept sharing before asking." }); return; }
   locked.current = true;
   result.mutate(values.question);
  })(event); }}>
   <label className="block" htmlFor={input}>Your question about the paper</label>
   <textarea id={input} rows={3} maxLength={500} disabled={result.isPending || exhausted} className="w-full rounded border border-border bg-background p-2" {...form.register("question")}/>
   {form.formState.errors.question && <p role="alert">{form.formState.errors.question.message}</p>}
   <label className="flex items-start gap-2"><input type="checkbox" disabled={result.isPending || exhausted} {...form.register("accepted")}/>I agree to send my questions and retrieved paper text to {status.provider} while using this form.</label>
   {form.formState.errors.accepted && <p role="alert">{form.formState.errors.accepted.message}</p>}
   <Button disabled={result.isPending || exhausted}>{result.isPending ? "Checking the paper…" : "Ask the paper"}</Button>
  </form>
  {result.isPending && <p role="status">Finding evidence and checking the answer. This may take up to a minute.</p>}
  {result.error && <p role="alert">{result.error.message} No automatic retry was sent.</p>}
  {!result.isPending && !result.error && result.data && <div className="space-y-3" aria-live="polite">
   <p className="text-sm">Question: {result.variables}</p>
   {result.data.status === "insufficient_evidence" ? <p>There isn’t enough supported evidence in the retrieved excerpts to answer. Try finding passages or reading the source pages.</p> :
    result.data.status === "unavailable" ? <p>The answer could not be completed or verified. No answer is shown. You can still search the paper’s passages.</p> :
    <ol className="space-y-3">{result.data.claims.map((claim, index) => <li key={index} className="space-y-2 rounded border border-border p-3">
     <p className="break-words">{claim.text}</p>
     {claim.citations.map((citation, n) => <div key={n} className="space-y-2"><blockquote className="whitespace-pre-wrap break-words text-sm">{citation.quote}</blockquote><Button variant="outline" onClick={() => onPage(citation.page)}>Read cited page {citation.page}</Button></div>)}
    </li>)}</ol>}
   <p className="text-sm text-muted-foreground">{result.data.notice}</p>
  </div>}
 </div>;
}
