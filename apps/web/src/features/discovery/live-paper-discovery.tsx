"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { BookOpen, Database, FileSearch, RefreshCw, Search, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
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
  type DiscoveredPaper,
  type LivePaperSearchForm,
  type LivePaperSearchFormInput,
} from "@/features/discovery/contracts";
import { discoverOpenAlexPapers } from "@/lib/api/discovery";
import { ApiError } from "@/lib/api/result";

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

function PaperResult({ index, paper }: { index: number; paper: DiscoveredPaper }) {
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

        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <div>
            <h4 className="text-xs font-bold tracking-[0.12em] text-muted-foreground uppercase">
              Paper authorships
            </h4>
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
              OpenAlex topic metadata
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

export function LivePaperDiscovery() {
  const [activeController, setActiveController] = useState<AbortController | null>(null);
  const mutation = useMutation({ mutationFn: discoverOpenAlexPapers });
  const {
    formState: { errors },
    handleSubmit,
    register,
  } = useForm<LivePaperSearchFormInput, unknown, LivePaperSearchForm>({
    defaultValues: { query: defaultQuery, limit: 12 },
    resolver: zodResolver(livePaperSearchFormSchema),
  });

  useEffect(() => () => activeController?.abort(), [activeController]);

  function submit(values: LivePaperSearchForm) {
    const controller = new AbortController();
    setActiveController(controller);
    mutation.mutate({ ...values, signal: controller.signal });
  }

  const error = mutation.error instanceof ApiError ? mutation.error : null;
  const result = mutation.data;

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
              <FieldLabel htmlFor="live-paper-query">Topic, DOI, or OpenAlex Work ID</FieldLabel>
              <Input
                aria-invalid={Boolean(errors.query)}
                id="live-paper-query"
                placeholder="e.g. interpretable ML for clinical decisions"
                {...register("query")}
              />
              <FieldError errors={[errors.query]} />
            </Field>
            <Field data-invalid={Boolean(errors.limit)}>
              <FieldLabel htmlFor="live-paper-limit">Result limit</FieldLabel>
              <NativeSelect id="live-paper-limit" {...register("limit")}>
                <option value="6">6 papers</option>
                <option value="12">12 papers</option>
                <option value="20">20 papers</option>
              </NativeSelect>
              <FieldError errors={[errors.limit]} />
            </Field>
            <Button disabled={mutation.isPending} type="submit" variant="evidence">
              <Search aria-hidden="true" />
              {mutation.isPending ? "Searching…" : "Search OpenAlex"}
            </Button>
          </div>
          <FieldDescription className="mt-4 border-t border-border pt-4">
            Real provider retrieval. Results are validated, deduplicated, persisted with provenance, and shown in OpenAlex order—not Research Bridge ranked.
          </FieldDescription>
        </form>

        <div aria-live="polite" className="mt-8">
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
                        limit: mutation.variables.limit,
                        query: mutation.variables.query,
                      })
                    }
                    variant="outline"
                  >
                    <RefreshCw aria-hidden="true" />
                    Retry request
                  </Button>
                ) : null
              }
              description={`${error?.message ?? "The live paper request could not be completed."}${error?.requestId ? ` Request reference: ${error.requestId}.` : ""}`}
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
                    OpenAlex provider order · not Research Bridge ranked
                  </p>
                  <h2 className="mt-2 text-3xl font-medium" id="live-results-title">
                    Reviewable publication evidence
                  </h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Query type: {result.queryKind} · Retrieved {formatRetrievedAt(result.source.retrievedAt)} UTC
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <StatusBadge tone="evidence">{result.returnedCount} papers</StatusBadge>
                  <StatusBadge>{result.source.cacheStatus === "hit" ? "Provider cache hit" : "Fresh provider response"}</StatusBadge>
                </div>
              </div>
              <div className="divide-y divide-border border-b border-border">
                {result.papers.map((paper, index) => (
                  <PaperResult index={index} key={paper.id} paper={paper} />
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
        <h2 className="mt-5 text-xl font-medium">What live discovery proves</h2>
        <ul className="mt-4 space-y-4 text-sm leading-6 text-muted-foreground">
          <li className="flex gap-2"><FileSearch aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Typed OpenAlex retrieval with bounded retries and visible partial failures.</li>
          <li className="flex gap-2"><Database aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Normalized papers, authors, affiliations, topics, and provenance persist in PostgreSQL.</li>
          <li className="flex gap-2"><ShieldCheck aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Unknown fields stay unknown; retracted and invalid records are not silently recommended.</li>
          <li className="flex gap-2"><BookOpen aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Mentor derivation and transparent relevance arrive in Phase 7.</li>
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
