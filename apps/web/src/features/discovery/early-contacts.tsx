"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { contactResponseSchema } from "@/features/mentors/contact-contracts";
import { findPublicEmail } from "@/lib/api/contact";
import { useResearchTask } from "./research-session";
import type { DiscoveredPaper } from "./contracts";

export const CONTACT_PASS_LIMIT = 6;
const resultsSchema = z.record(z.string(), z.object({
  result: contactResponseSchema.nullable(), error: z.string().nullable(),
}));
const batchSchema = z.object({ signature: z.string(), results: resultsSchema });
const requestSchema = z.object({ signature: z.string(), authors: z.array(z.string()) });
export type EarlyContacts = z.infer<typeof resultsSchema>;

// Breadth first: one author per paper before checking a paper's other authors.
export function prioritizedAuthors(papers: DiscoveredPaper[]): string[] {
  const queues = papers.map(p => [...p.authors].sort((a,b) => Number(!!b.isCorresponding) - Number(!!a.isCorresponding)));
  const ids = new Set<string>();
  for (let depth = 0; depth < Math.max(0, ...queues.map(q => q.length)); depth++) {
    for (const queue of queues) {
      if (queue[depth]) ids.add(queue[depth].id);
      if (ids.size === CONTACT_PASS_LIMIT) return [...ids];
    }
  }
  return [...ids];
}

export function useEarlyContacts(papers: DiscoveredPaper[]) {
  const client = useQueryClient();
  const authors = prioritizedAuthors(papers);
  const signature = authors.join(",");
  const task = useResearchTask("early-contacts", batchSchema, requestSchema, async (values, signal, emit) => {
    const results: EarlyContacts = {};
    let next = 0;
    const publish = () => emit({ signature: values.signature, results: { ...results } });
    publish();
    async function worker() {
      while (!signal.aborted && next < values.authors.length) {
        const id = values.authors[next++];
        try {
          const cached = client.getQueryData<{data?: unknown}>(["research", `public-email-${id}`]);
          const parsed = contactResponseSchema.safeParse(cached?.data);
          const maxAge = parsed.success && parsed.data.status === "found" ? 7 * 86400000 : 3600000;
          const fresh = parsed.success && Date.now() - Date.parse(parsed.data.checkedAt) < maxAge;
          const result = fresh && parsed.success ? parsed.data : await findPublicEmail(id, {}, signal);
          if (signal.aborted) return;
          results[id] = { result, error: null };
          // Same persisted key as the detailed public-email view, so opening an
          // author exposes this evidence without another student-triggered lookup.
          client.setQueryData(["research", `public-email-${id}`], {
            data: result, variables: {}, status: "success", error: null, startedAt: null,
          });
        } catch (error) {
          if (signal.aborted) return;
          results[id] = { result: null, error: error instanceof Error ? error.message : "Lookup unavailable" };
        }
        publish();
      }
    }
    await Promise.all([worker(), worker()]);
    return { signature: values.signature, results };
  });
  const previousSignature = task.variables?.signature;
  const start = task.mutate;
  useEffect(() => {
    if (signature && signature !== previousSignature) start({ signature, authors: signature.split(",") });
  }, [signature, previousSignature, start]);
  return {
    ...task,
    results: task.data?.signature === signature ? task.data.results : {},
    authors,
    restart: () => start({ signature, authors }),
  };
}

export function hasPublicContact(paper: DiscoveredPaper, results: EarlyContacts) {
  return paper.authors.some(a => results[a.id]?.result?.status === "found" && results[a.id].result!.emails.length > 0);
}

export function PaperContactSummary({ paper, results, queued, pending }: {
  paper: DiscoveredPaper; results: EarlyContacts; queued: string[]; pending: boolean;
}) {
  const found = paper.authors.filter(a => results[a.id]?.result?.status === "found" && results[a.id].result!.emails.length > 0);
  const checked = paper.authors.filter(a => results[a.id]);
  const waiting = paper.authors.some(a => queued.includes(a.id) && !results[a.id]);
  const incomplete = checked.some(a => results[a.id].error || ["blocked", "unsupported", "needs-review"].includes(results[a.id].result?.status ?? ""));
  const label = found.length ? `Public email found for ${found.length} ${found.length === 1 ? "author" : "authors"}`
    : pending && waiting ? "Checking public emails…"
    : incomplete ? "Contact lookup incomplete — review author details"
    : checked.length ? "No public email found in the pages checked" : "Authors not checked yet";
  return <div className="mt-4 space-y-2 rounded border border-border p-3 text-sm">
    <p className="font-medium">{label}</p>
    <p className="text-xs text-muted-foreground">{checked.length} of {paper.authors.length} authors checked. Source evidence does not confirm deliverability or availability.</p>
    {found.map(author => <div key={author.id} className="flex flex-wrap gap-x-4 gap-y-1">
      <Link className="underline" href={`/mentors?paper=${paper.id}&author=${author.id}`}>Contact {author.displayName}</Link>
      {results[author.id].result?.emails.map(email => <a key={email.email} className="break-all underline" href={email.sourceUrl} target="_blank" rel="noopener noreferrer">{email.email} · source</a>)}
    </div>)}
  </div>;
}

export function EarlyContactProgress({ task }: { task: ReturnType<typeof useEarlyContacts> }) {
  return <div className="my-4 space-y-2 text-sm">
    <p role="status">{task.isPending ? "Checking official pages in the background" : "First contact-check pass"}: {Object.keys(task.results).length} / {task.authors.length} authors.</p>
    <p className="text-xs text-muted-foreground">Up to six distinct authors per search, two at a time. Each lookup allows up to 90 seconds; the first pass can take about 5 minutes. Other authors remain available for individual lookup. You can switch sections while checks continue.</p>
    {task.isPending && <Button size="sm" variant="outline" onClick={task.cancel}>Stop contact checks</Button>}
    {!task.isPending && (["cancelled", "interrupted", "error"].includes(task.status) || Object.values(task.results).some(value => value.error)) && <Button size="sm" variant="outline" onClick={task.restart}>Resume contact checks</Button>}
  </div>;
}
