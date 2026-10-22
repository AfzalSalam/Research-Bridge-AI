"use client";

import { z } from "zod";
import { useEarlyContacts, hasPublicContact, PaperContactSummary, EarlyContactProgress, type EarlyContacts } from "./early-contacts";

import { zodResolver } from "@hookform/resolvers/zod";
import { useResearchTask, useResearchValue } from "@/features/discovery/research-session";
import { BookOpen, Database, FileSearch, RefreshCw, Search, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { DataState } from "@/components/states/data-state";
import { StatusBadge } from "@/components/status/status-badge";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { EvidenceLink } from "@/features/demo/components/evidence-link";
import { NativeSelect } from "@/features/demo/components/native-select";
import {
  livePaperSearchFormSchema,
  paperDiscoveryResponseSchema,
  type DiscoveredPaper,
  type LivePaperSearchForm,
  type LivePaperSearchFormInput,
} from "@/features/discovery/contracts";
import { discoverOpenAlexPapers } from "@/lib/api/discovery";


const defaultQuery = "interpretable machine learning for clinical decision support";

function formatRetrievedAt(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

function metadataLabel(paper: DiscoveredPaper): string {
  return [
    String(paper.publicationYear),
    paper.venue ?? "Venue unknown",
    paper.workType ?? "Type unknown",
  ].join(" · ");
}

function PaperResult({ index, paper, contacts, queued, pending }: { index: number; paper: DiscoveredPaper; contacts: EarlyContacts; queued: string[]; pending: boolean }) {
  return (
    <article className="grid gap-5 py-8 md:grid-cols-[3rem_minmax(0,1fr)]">
      <span className="grid size-10 place-items-center rounded-full bg-brand-indigo-soft text-sm font-bold text-brand-indigo">
        {String(index + 1).padStart(2, "0")}
      </span>
      <div className="min-w-0">
        <div className="flex flex-wrap gap-2">
          <StatusBadge tone={paper.evidenceStrength === "full-abstract" ? "evidence" : "unknown"}>
            {paper.evidenceStrength === "full-abstract" ? "Abstract evidence" : "Title-only evidence"}
          </StatusBadge>
          {paper.language ? <StatusBadge>{paper.language.toUpperCase()}</StatusBadge> : null}
        </div>
        <h3 className="mt-4 text-2xl font-medium tracking-[-0.02em] text-balance">
          {paper.title}
        </h3>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {metadataLabel(paper)}
        </p>

        {paper.abstractExcerpt ? (
          <p className="mt-5 max-w-3xl text-sm leading-7 text-foreground">
            {paper.abstractExcerpt}
          </p>
        ) : (
          <p className="mt-5 max-w-3xl border-l-2 border-warning pl-4 text-sm leading-7 text-muted-foreground">
            OpenAlex supplied title metadata but no validated abstract. Research Bridge will not infer methods or findings from the title.
          </p>
        )}

        <PaperContactSummary paper={paper} results={contacts} queued={queued} pending={pending} />
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <div>
            <h4 className="text-xs font-bold tracking-[0.12em] text-muted-foreground uppercase">Authors of this paper</h4>
            <p className="mt-2 text-xs text-muted-foreground">Authors may be students or researchers. A paper does not confirm a professor role or internship opening.</p>
            {paper.authors.length ? (
              <ul className="mt-3 space-y-3">
                {paper.authors.map((author) => (
                  <li className="text-sm leading-6" key={author.id}>
                    <EvidenceLink href={author.sourceUrl}>{author.displayName}</EvidenceLink>
                    {author.isCorresponding ? (
                      <span className="ml-2 text-xs text-brand-teal-strong">Corresponding</span>
                    ) : null}
                    <p className="text-muted-foreground">
                      {author.institutions.length
                        ? author.institutions.map((item) => item.displayName).join("; ")
                        : "Affiliation unknown for this paper"}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">Author metadata unknown.</p>
            )}
          </div>
          <div>
            <h4 className="text-xs font-bold tracking-[0.12em] text-muted-foreground uppercase">
              Research topics
            </h4>
            {paper.topics.length ? (
              <ul className="mt-3 flex flex-wrap gap-2">
                {paper.topics.map((topic) => (
                  <li className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground" key={topic.id}>
                    {topic.displayName}
                    {topic.score === null ? "" : ` · ${topic.score.toFixed(2)} provider score`}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">Topic metadata unknown.</p>
            )}
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-x-5 gap-y-3 border-t border-border pt-5">
          <EvidenceLink href={paper.sourceUrl}>OpenAlex work record</EvidenceLink>
          <Link className="text-sm underline" href={`/research/papers/${paper.id}`}>Read, save, and contact authors</Link>
          {paper.doi ? (
            <EvidenceLink href={`https://doi.org/${paper.doi}`}>DOI record</EvidenceLink>
          ) : (
            <span className="text-sm text-muted-foreground">DOI unknown</span>
          )}
        </div>
      </div>
    </article>
  );
}

const persistedFormSchema = livePaperSearchFormSchema.extend({ query: z.string().max(300) });

export function LivePaperDiscovery() {
  const mutation = useResearchTask("paper-search", paperDiscoveryResponseSchema, livePaperSearchFormSchema, (values, signal) => discoverOpenAlexPapers({ ...values, signal }));
  const [savedForm, setSavedForm] = useResearchValue("paper-search-form", persistedFormSchema, { query: defaultQuery, limit: 20 });
  const {
    subscribe,
    formState: { errors },
    handleSubmit,
    register,
  } = useForm<LivePaperSearchFormInput, unknown, LivePaperSearchForm>({
    defaultValues: savedForm,
    resolver: zodResolver(livePaperSearchFormSchema),
  });

  useEffect(() => subscribe({ formState: { values: true }, callback: ({ values }) => { const parsed = persistedFormSchema.safeParse(values); if (parsed.success) setSavedForm(parsed.data); } }), [subscribe, setSavedForm]);

  function submit(values: LivePaperSearchForm) {
    mutation.mutate(values);
  }

  const error = mutation.error;
  const result = mutation.data;
  const contacts = useEarlyContacts(result?.papers ?? []);
  const [contactableOnly, setContactableOnly] = useResearchValue("papers-contactable-only", z.boolean(), false);

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-start">
      <section className="min-w-0">
        <form
          className="border border-border bg-surface p-5 sm:p-7"
          noValidate
          onSubmit={handleSubmit(submit)}
        >
          <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_8rem_auto] md:items-end">
            <Field data-invalid={Boolean(errors.query)}>
              <FieldLabel htmlFor="live-paper-query">What topic interests you?</FieldLabel>
              <Input
                aria-invalid={Boolean(errors.query)}
                id="live-paper-query"
                placeholder="e.g. interpretable ML for clinical decisions"
                {...register("query")}
              />
              <FieldError errors={[errors.query]} />
            </Field>
            <Field data-invalid={Boolean(errors.limit)}>
              <FieldLabel htmlFor="live-paper-limit">Number of papers</FieldLabel>
              <NativeSelect id="live-paper-limit" {...register("limit")}>
                <option value="10">10 papers</option>
                <option value="20">20 papers</option>
                <option value="30">30 papers</option>
              </NativeSelect>
              <FieldError errors={[errors.limit]} />
            </Field>
            <Button disabled={mutation.isPending} type="submit" variant="evidence">
              <Search aria-hidden="true" />
              {mutation.isPending ? "Searching…" : "Search papers"}
            </Button>
          </div>
          <FieldDescription className="mt-4 border-t border-border pt-4">
            Search academic papers through OpenAlex. Read a paper, explore its authors, then choose someone to contact.
          </FieldDescription>
          <div className="mt-4 flex flex-wrap gap-3">
            {mutation.isPending && <Button type="button" variant="outline" onClick={mutation.cancel}>Cancel search</Button>}
            {mutation.data && !mutation.isPending && <Button type="button" variant="outline" onClick={mutation.clear}>Clear results</Button>}
          </div>
        </form>

        <div aria-live="polite" className="mt-8">
          {mutation.status === "interrupted" && <p className="mb-4 text-sm">Search interrupted by refresh. Received results are kept; search again when ready.</p>}
          {!mutation.isPending && !mutation.isError && !result ? (
            <DataState
              description="Search a focused topic, paste a DOI, or enter an OpenAlex Work ID. No LLM rewrites the query or invents publication details."
              kind="empty"
              title="Ready to retrieve real paper evidence"
            />
          ) : null}

          {mutation.isPending ? (
            <DataState
              description="The server is contacting OpenAlex, validating each returned work, normalizing evidence, and persisting provenance."
              kind="loading"
              title="Retrieving publication evidence"
            />
          ) : null}

          {mutation.isError ? (
            <DataState
              action={
                mutation.variables ? (
                  <Button
                    onClick={() =>
                      submit({
                        limit: mutation.variables!.limit,
                        query: mutation.variables!.query,
                      })
                    }
                    variant="outline"
                  >
                    <RefreshCw aria-hidden="true" />
                    Retry request
                  </Button>
                ) : null
              }
              description={`${error ?? "The live paper request could not be completed."}`}
              kind="error"
              title="OpenAlex evidence is unavailable"
            />
          ) : null}

          {result?.status === "empty" ? (
            <DataState
              description="OpenAlex returned no reviewable work for this normalized query. Check the identifier or broaden the topic wording."
              kind="empty"
              title="No paper evidence found"
            />
          ) : null}

          {result?.status === "partial" ? (
            <DataState
              className="mb-6 min-h-0"
              description={`${result.returnedCount} valid papers remain visible. ${result.skippedCount} record${result.skippedCount === 1 ? " was" : "s were"} skipped: ${result.warnings.join(" ")}`}
              kind="partial"
              title="OpenAlex returned partial evidence"
            />
          ) : null}

          {result && result.papers.length ? (
            <section aria-labelledby="live-results-title">
              <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-4">
                <div>
                  <p className="text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">
                    Academic database results
                  </p>
                  <h2 className="mt-2 text-3xl font-medium" id="live-results-title">
                    Papers on your topic
                  </h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Query type: {result.queryKind} · Retrieved {formatRetrievedAt(result.source.retrievedAt)} UTC
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <StatusBadge tone="evidence">{result.returnedCount} papers</StatusBadge>
                  <StatusBadge>{result.source.cacheStatus === "hit" ? "Provider cache hit" : "Fresh provider response"}</StatusBadge>
                  <Button asChild size="sm" variant="outline">
                    <Link href={`/mentors?query=${encodeURIComponent(result.query)}`}>
                      Find Professors
                    </Link>
                  </Button>
                </div>
              </div>
              <EarlyContactProgress task={contacts} />
              <label className="mb-4 flex items-center gap-2 text-sm"><input type="checkbox" checked={contactableOnly} onChange={e => setContactableOnly(e.target.checked)} />Only papers with a public email found</label>
              {contactableOnly && !result.papers.some(p => hasPublicContact(p, contacts.results)) && <p role="status">No papers match this filter yet. Checks may be incomplete; turn off the filter to see all relevant papers.</p>}
              <div className="divide-y divide-border border-b border-border">
                {result.papers.filter(paper => !contactableOnly || hasPublicContact(paper, contacts.results)).map((paper, index) => (
                  <PaperResult index={index} key={paper.id} paper={paper} contacts={contacts.results} queued={contacts.authors} pending={contacts.isPending} />
                ))}
              </div>
            </section>
          ) : null}
        </div>
      </section>

      <aside className="border border-border bg-surface-subtle p-6 lg:sticky lg:top-24">
        <div className="grid size-10 place-items-center rounded-full bg-brand-teal-soft text-brand-teal-strong">
          <Database aria-hidden="true" className="size-5" />
        </div>
        <h2 className="mt-5 text-xl font-medium">What to do next</h2>
        <ul className="mt-4 space-y-4 text-sm leading-6 text-muted-foreground">
          <li className="flex gap-2"><FileSearch aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Start with a specific topic, such as computer vision for medical images.</li>
          <li className="flex gap-2"><Database aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Open a paper and review the authors together, including their affiliations at publication.</li>
          <li className="flex gap-2"><ShieldCheck aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Unknown fields stay unknown; retracted and invalid records are not silently recommended.</li>
          <li className="flex gap-2"><BookOpen aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Use Find Professors to review an author’s work and prepare an email draft.</li>
        </ul>
        <p className="mt-6 border-t border-border pt-5 text-xs leading-5 text-muted-foreground">
          {result?.source.accessMode === "limited-anonymous"
            ? "This server is using OpenAlex's limited anonymous allowance. A server-only API key increases the free daily budget."
            : "The server used its configured OpenAlex API allowance. The key never enters browser code."}
        </p>
      </aside>
    </div>
  );
}
