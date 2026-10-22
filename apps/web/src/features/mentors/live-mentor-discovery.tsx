"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useResearchTask, useResearchValue } from "@/features/discovery/research-session";
import {
  ArrowLeft,
  BookOpen,
  Database,
  FileSearch,
  RefreshCw,
  Scale,
  Search,
  ShieldQuestion,
  UserRoundSearch,
} from "lucide-react";
import { useEffect, useRef } from "react";
import { useForm } from "react-hook-form";

import { DataState } from "@/components/states/data-state";
import { StatusBadge } from "@/components/status/status-badge";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { EvidenceLink } from "@/features/demo/components/evidence-link";
import { LiveOutreachWorkspace } from "@/features/outreach/live-outreach-workspace";
import { NativeSelect } from "@/features/demo/components/native-select";
import {
  liveMentorSearchFormSchema,
  mentorDiscoveryResponseSchema,
  type LiveMentorSearchForm,
  type LiveMentorSearchFormInput,
  type MentorCandidateResult,
  type MentorDiscoveryResponse,
} from "@/features/discovery/contracts";
import { discoverOpenAlexMentors } from "@/lib/api/mentors";

import { cn } from "@/lib/utils";

import { PublicEmailLookup } from "./public-email-lookup";
import { PaperAuthorGroups } from "./paper-author-groups";

const fallbackQuery = "interpretable machine learning for clinical decision support";
const bandLabel = {
  strong: "Strong evidence overlap",
  promising: "Promising evidence overlap",
  exploratory: "Exploratory evidence overlap",
} as const;

function CandidateList({
  candidates,
  onSelect,
  selectedId,
}: {
  candidates: MentorCandidateResult[];
  onSelect: (id: string) => void;
  selectedId: string | null;
}) {
  return (
    <section aria-labelledby="candidate-list-title">
      <div className="border-b border-border pb-4">
        <p className="text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">
          Matched through their publications
        </p>
        <h2 className="mt-2 text-2xl font-medium" id="candidate-list-title">
          Research authors
        </h2>
      </div>
      <div className="divide-y divide-border border-b border-border">
        {candidates.map((candidate, index) => (
          <button
            aria-pressed={candidate.id === selectedId}
            className={cn(
              "block w-full border-l-2 px-4 py-5 text-left transition-colors hover:bg-muted/70 focus-visible:outline-offset-[-3px] motion-reduce:transition-none",
              candidate.id === selectedId
                ? "border-l-brand-teal bg-brand-teal-soft/55"
                : "border-l-transparent bg-surface",
            )}
            id={`candidate-${candidate.id}`}
            key={candidate.id}
            onClick={() => onSelect(candidate.id)}
            type="button"
          >
            <span className="flex items-start gap-3">
              <span className="grid size-8 shrink-0 place-items-center rounded-full bg-brand-indigo-soft text-xs font-bold text-brand-indigo">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="min-w-0">
                <span className="block font-serif text-xl font-medium">
                  {candidate.displayName}
                </span>
                <span className="mt-1 block text-sm leading-6 text-muted-foreground">
                  Academic title and current institution unknown
                </span>
              </span>
            </span>
            <span className="mt-4 flex flex-wrap gap-2">
              <StatusBadge tone="evidence">
                {bandLabel[candidate.relevanceBand]}
              </StatusBadge>
              <StatusBadge>
                {candidate.supportingPaperCount} paper
                {candidate.supportingPaperCount === 1 ? "" : "s"}
              </StatusBadge>
            </span>
            {candidate.researchThemes.length ? (
              <span className="mt-3 block text-sm leading-6 text-muted-foreground">
                {candidate.researchThemes.slice(0, 3).join(" · ")}
              </span>
            ) : null}
          </button>
        ))}
      </div>
    </section>
  );
}

function Contributions({ candidate }: { candidate: MentorCandidateResult }) {
  return (
    <section className="mt-9" aria-labelledby="contribution-title">
      <div className="flex items-center gap-3">
        <Scale aria-hidden="true" className="size-5 text-brand-indigo" />
        <h3 className="text-2xl font-medium" id="contribution-title">
          Why this candidate appears here
        </h3>
      </div>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
        These auditable inputs control ordering. Research Bridge intentionally avoids
        a misleading overall compatibility percentage.
      </p>
      <div className="mt-5 divide-y divide-border border-y border-border">
        {candidate.contributions.map((item) => (
          <article className="py-5" key={item.feature}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h4 className="font-semibold">{item.label}</h4>
              <span className="text-xs font-bold tracking-wide text-brand-indigo uppercase">
                {Math.round(item.value * 100)}% evidence · {Math.round(item.weight * 100)}% weight
              </span>
            </div>
            <div
              aria-label={`${item.label}: ${Math.round(item.value * 100)} percent evidence coverage`}
              className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted"
              role="img"
            >
              <div
                className="h-full rounded-full bg-gradient-to-r from-brand-teal to-brand-indigo"
                style={{ width: `${Math.round(item.value * 100)}%` }}
              />
            </div>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              {item.explanation}
            </p>
            {item.matchedTerms.length ? (
              <ul className="mt-3 flex flex-wrap gap-2" aria-label="Matched terms">
                {item.matchedTerms.map((term) => (
                  <li
                    className="rounded-full bg-brand-teal-soft px-3 py-1 text-xs text-brand-teal-strong"
                    key={term}
                  >
                    {term}
                  </li>
                ))}
              </ul>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

function Papers({ candidate }: { candidate: MentorCandidateResult }) {
  return (
    <section className="mt-9" aria-labelledby="paper-evidence-title">
      <div className="flex items-center gap-3">
        <BookOpen aria-hidden="true" className="size-5 text-brand-indigo" />
        <h3 className="text-2xl font-medium" id="paper-evidence-title">
          Publication evidence
        </h3>
      </div>
      <div className="mt-4 divide-y divide-border border-y border-border">
        {candidate.supportingPapers.map((paper) => (
          <article className="py-6" key={paper.id}>
            <div className="flex flex-wrap gap-2">
              <StatusBadge tone="evidence">{paper.publicationYear}</StatusBadge>
              <StatusBadge tone={paper.abstractExcerpt ? "neutral" : "unknown"}>
                {paper.abstractExcerpt ? "Abstract evidence" : "Title-only evidence"}
              </StatusBadge>
              <StatusBadge>Author position {paper.authorship.position}</StatusBadge>
            </div>
            <h4 className="mt-4 text-xl font-medium leading-7">{paper.title}</h4>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {[
                paper.venue ?? "Venue unknown",
                paper.workType ?? "Type unknown",
                paper.language?.toUpperCase() ?? "Language unknown",
              ].join(" · ")}
              {paper.authorship.isCorresponding ? " · Corresponding author" : ""}
            </p>
            {paper.abstractExcerpt ? (
              <p className="mt-4 max-w-3xl text-sm leading-7">{paper.abstractExcerpt}</p>
            ) : (
              <p className="mt-4 border-l-2 border-warning pl-4 text-sm leading-6 text-muted-foreground">
                No validated abstract is available, so no finding is inferred from
                this title.
              </p>
            )}
            <div className="mt-5 grid gap-5 md:grid-cols-2">
              <div>
                <p className="text-xs font-bold tracking-[0.12em] text-muted-foreground uppercase">
                  Affiliations at publication
                </p>
                {paper.authorship.affiliationsAtPublication.length ? (
                  <ul className="mt-2 space-y-2 text-sm leading-6">
                    {paper.authorship.affiliationsAtPublication.map((institution) => (
                      <li key={institution.id}>
                        <EvidenceLink href={institution.sourceUrl}>
                          {institution.displayName}
                        </EvidenceLink>
                        {institution.countryCode ? ` · ${institution.countryCode}` : ""}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-muted-foreground">Unknown</p>
                )}
              </div>
              <div>
                <p className="text-xs font-bold tracking-[0.12em] text-muted-foreground uppercase">
                  OpenAlex topics
                </p>
                {paper.topics.length ? (
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {paper.topics.map((topic) => topic.displayName).join(" · ")}
                  </p>
                ) : (
                  <p className="mt-2 text-sm text-muted-foreground">Unknown</p>
                )}
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 border-t border-border pt-4">
              <EvidenceLink href={paper.sourceUrl}>OpenAlex work record</EvidenceLink>
              {paper.doi ? (
                <EvidenceLink href={`https://doi.org/${paper.doi}`}>DOI record</EvidenceLink>
              ) : (
                <span className="text-sm text-muted-foreground">DOI unknown</span>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function CandidateDetail({
  candidate,
  onBack,
  query,
}: {
  candidate: MentorCandidateResult;
  onBack: () => void;
  query: string;
}) {
  const [savedIds, setSavedIds] = useResearchValue("saved-researchers", z.array(z.string()), []);
  const saved = savedIds.includes(candidate.id);
  return (
    <article id="researcher-detail" tabIndex={-1} className="scroll-mt-24">
      <Button className="mb-5 lg:hidden" onClick={onBack} size="sm" variant="outline">
        <ArrowLeft aria-hidden="true" /> Back to candidates
      </Button>
      <div className="flex flex-wrap gap-2">
        <StatusBadge tone="evidence">{bandLabel[candidate.relevanceBand]}</StatusBadge>
        <StatusBadge>{candidate.evidenceConfidence} evidence confidence</StatusBadge>
        <StatusBadge tone="unknown">Availability unknown</StatusBadge>
      </div>
      <h2 className="mt-5 text-4xl font-medium tracking-[-0.03em] text-balance">
        {candidate.displayName}
      </h2>
      <p className="mt-2 text-base leading-7 text-muted-foreground">
        Research author found through {candidate.supportingPaperCount} validated
        publication{candidate.supportingPaperCount === 1 ? "" : "s"}
      </p>
      <div className="mt-7 grid gap-px border border-border bg-border sm:grid-cols-3">
        {["Academic title", "Current institution", "Open to students"].map((label) => (
          <div className="bg-surface p-4" key={label}>
            <p className="text-xs font-bold tracking-[0.1em] text-muted-foreground uppercase">
              {label}
            </p>
            <p className="mt-2 font-medium text-warning-foreground">Unknown</p>
          </div>
        ))}
      </div>
      <div className="mt-6 flex flex-wrap gap-x-5 gap-y-3">
        <EvidenceLink href={candidate.sourceUrl}>OpenAlex author record</EvidenceLink>
        {candidate.orcid ? (
          <EvidenceLink href={candidate.orcid}>ORCID identifier</EvidenceLink>
        ) : (
          <span className="text-sm text-muted-foreground">ORCID unknown</span>
        )}
      </div>
      <p className="mt-7 border-l-2 border-warning bg-warning-soft p-4 text-sm leading-6 text-warning-foreground">
        Publication affiliations are historical paper evidence, never a claim about
        the author&apos;s current employer. Verify identity, title, lab page, and
        openings before outreach.
      </p>
      <PublicEmailLookup authorId={candidate.id} authorName={candidate.displayName} />
      <details className="mt-6"><summary className="cursor-pointer text-sm font-medium">How are these results ordered?</summary><Contributions candidate={candidate} /></details>
      <div className="mt-6 flex flex-wrap items-center gap-4 text-sm">
        <a href="#paper-evidence-title" className="underline">View papers</a>
        <a href="#researcher-email" className="underline">Draft an email</a>
        <Button variant="outline" aria-pressed={saved} onClick={() => setSavedIds((old) => saved ? old.filter((id) => id !== candidate.id) : [...old, candidate.id])}>{saved ? "Saved for this session" : "Save researcher for this session"}</Button>
      </div>
      <Papers candidate={candidate} />
      <div id="researcher-email" className="scroll-mt-24"><LiveOutreachWorkspace candidate={candidate} key={candidate.id} query={query} /></div>
    </article>
  );
}

function ResultWorkspace({ result }: { result: MentorDiscoveryResponse }) {
  const [selectedId, setSelectedId] = useResearchValue("mentor-selected", z.string().nullable(), result.candidates[0]?.id ?? null);
  const lastSelectedId = useRef<string | null>(selectedId);
  const selected = result.candidates.find((item) => item.id === selectedId);

  const pendingFocus = useRef<"detail" | "list" | null>(null);
  useEffect(() => {
    if (pendingFocus.current === "detail") {
      const detail = document.getElementById("researcher-detail");
      detail?.scrollIntoView({ block: "start" });
      detail?.focus({ preventScroll: true });
    } else if (pendingFocus.current === "list" && lastSelectedId.current) {
      document.getElementById(`candidate-${lastSelectedId.current}`)?.focus();
    }
    pendingFocus.current = null;
  }, [selectedId]);

  function selectCandidate(id: string) {
    lastSelectedId.current = id;
    if (id === selectedId) {
      document.getElementById("researcher-detail")?.focus();
      return;
    }
    pendingFocus.current = "detail";
    setSelectedId(id);
  }

  function returnToCandidates() {
    pendingFocus.current = "list";
    setSelectedId(null);
  }
  return (
    <>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
        <div>
          <p className="text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">
            Choose a person, read their papers, then review an email draft
          </p>
          <h2 className="mt-2 text-3xl font-medium">People working on your topic</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {result.paperCount} papers · {result.authorAppearanceCount} authorships
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge tone="evidence">{result.returnedCount} candidates</StatusBadge>
          <StatusBadge>
            {result.source.cacheStatus === "hit" ? "Provider cache hit" : "Fresh source data"}
          </StatusBadge>
        </div>
      </div>
      <PaperAuthorGroups candidates={result.candidates} onSelect={selectCandidate} />
      <div className="grid gap-8 lg:grid-cols-[21rem_minmax(0,1fr)] lg:items-start lg:gap-10">
        <div className={cn(selected && "hidden lg:block", "lg:sticky lg:top-24")}>
          <CandidateList candidates={result.candidates} onSelect={selectCandidate} selectedId={selectedId} />
        </div>
        <div className={cn(!selected && "hidden lg:block")}>
          {selected ? (
            <CandidateDetail
              candidate={selected}
              key={selected.id}
              onBack={returnToCandidates}
              query={result.query}
            />
          ) : (
            <DataState description="Choose a candidate to inspect its evidence and uncertainty boundaries." kind="empty" title="Select a researcher" />
          )}
        </div>
      </div>
    </>
  );
}

const persistedFormSchema = liveMentorSearchFormSchema.extend({ query: z.string().max(300) });

export function LiveMentorDiscovery({ initialQuery }: { initialQuery?: string }) {
  const mutation = useResearchTask("mentor-search", mentorDiscoveryResponseSchema, liveMentorSearchFormSchema, (values, signal) => discoverOpenAlexMentors({ ...values, candidateLimit: 12, signal }));
  const [savedForm, setSavedForm] = useResearchValue("mentor-search-form", persistedFormSchema, { query: initialQuery || fallbackQuery, paperLimit: 20 });
  const {
    subscribe,
    reset: resetForm,
    formState: { errors },
    handleSubmit,
    register,
  } = useForm<LiveMentorSearchFormInput, unknown, LiveMentorSearchForm>({
    defaultValues: savedForm,
    resolver: zodResolver(liveMentorSearchFormSchema),
  });
  useEffect(() => subscribe({ formState: { values: true }, callback: ({ values }) => { const parsed = persistedFormSchema.safeParse(values); if (parsed.success) setSavedForm(parsed.data); } }), [subscribe, setSavedForm]);

  useEffect(() => { if (initialQuery) resetForm({ query: initialQuery, paperLimit: 20 }); }, [initialQuery, resetForm]);

  function submit(values: LiveMentorSearchForm) {
    mutation.mutate(values);
  }

  const error = mutation.error;
  const result = mutation.data;
  return (
    <div className="grid gap-8">
      <section className="min-w-0">
        <form className="border border-border bg-surface p-5 sm:p-7" noValidate onSubmit={handleSubmit(submit)}>
          <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_9rem_auto] md:items-end">
            <Field data-invalid={Boolean(errors.query)}>
              <FieldLabel htmlFor="live-mentor-query">What topic interests you?</FieldLabel>
              <Input aria-invalid={Boolean(errors.query)} id="live-mentor-query" placeholder="e.g. trustworthy ML for public health" {...register("query")} />
              <FieldError errors={[errors.query]} />
            </Field>
            <Field data-invalid={Boolean(errors.paperLimit)}>
              <FieldLabel htmlFor="live-mentor-paper-limit">Papers to search</FieldLabel>
              <NativeSelect id="live-mentor-paper-limit" {...register("paperLimit")}>
                <option value="10">10 papers</option>
                <option value="20">20 papers</option>
                <option value="30">30 papers</option>
              </NativeSelect>
              <FieldError errors={[errors.paperLimit]} />
            </Field>
            <Button disabled={mutation.isPending} type="submit" variant="evidence">
              <Search aria-hidden="true" /> {mutation.isPending ? "Searching…" : "Find researchers"}
            </Button>
          </div>
          <FieldDescription className="mt-4 border-t border-border pt-4">
            Find authors whose papers relate to your interests. Review their work before contacting them; not every author is a professor or accepting interns.
          </FieldDescription>
          <div className="mt-4 flex flex-wrap gap-3">
            {mutation.isPending && <Button type="button" variant="outline" onClick={mutation.cancel}>Cancel search</Button>}
            {mutation.data && !mutation.isPending && <Button type="button" variant="outline" onClick={mutation.clear}>Clear results</Button>}
          </div>
        </form>
        <div aria-live="polite" className="mt-8">
          {mutation.status === "interrupted" && <p className="mb-4 text-sm">Search interrupted by refresh. Received results are kept; search again when ready.</p>}
          {!mutation.isPending && !mutation.isError && !result ? (
            <DataState description="Search a focused topic to derive researchers from real publication authorships. Every connection exposes its evidence and unknowns." kind="empty" title="Who is working on your topic?" />
          ) : null}
          {mutation.isPending ? (
            <DataState description="Retrieving papers, consolidating repeated authors, calculating policy contributions, and checking evidence coverage." kind="loading" title="Finding papers and their authors" />
          ) : null}
          {mutation.isError ? (
            <DataState
              action={mutation.variables ? <Button onClick={() => submit({ paperLimit: mutation.variables!.paperLimit, query: mutation.variables!.query })} variant="outline"><RefreshCw aria-hidden="true" /> Retry request</Button> : null}
              description={`${error ?? "The researcher request could not be completed."}`}
              kind="error"
              title="Researcher evidence is unavailable"
            />
          ) : null}
          {result?.status === "empty" ? (
            <DataState description="OpenAlex returned no paper authors that can support a candidate. Broaden the topic or check the identifier." kind="empty" title="No evidence-backed researchers found" />
          ) : null}
          {result?.status === "partial" ? (
            <DataState className="mb-6 min-h-0" description={`${result.returnedCount} candidates remain reviewable. Some records were excluded: ${result.warnings.join(" ")}`} kind="partial" title="Candidate evidence is partial" />
          ) : null}
          {result && result.candidates.length ? <ResultWorkspace key={`${result.query}-${result.source.retrievedAt}`} result={result} /> : null}
        </div>
      </section>
      <aside className="grid gap-6 border border-border bg-surface-subtle p-6 lg:grid-cols-[11rem_minmax(0,1fr)_18rem] lg:items-start lg:gap-8">
        <div>
          <div className="grid size-10 place-items-center rounded-full bg-brand-teal-soft text-brand-teal-strong">
            <UserRoundSearch aria-hidden="true" className="size-5" />
          </div>
          <h2 className="mt-5 text-xl font-medium">Before you reach out</h2>
        </div>
        <ul className="grid gap-4 text-sm leading-6 text-muted-foreground sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
          <li className="flex gap-2"><Database aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Each person appears once, with links to the papers that connect them to your topic.</li>
          <li className="flex gap-2"><Scale aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Check the paper and the researcher’s official profile before deciding whom to contact.</li>
          <li className="flex gap-2"><ShieldQuestion aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Title, current employer, contact, and openings stay unknown until verified.</li>
          <li className="flex gap-2"><FileSearch aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Choose one person and relevant papers to prepare an email you can review and edit.</li>
        </ul>
        <div className="border-t border-border pt-5 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-6">
          <p className="text-xs font-bold tracking-[0.1em] text-muted-foreground uppercase">Profile context</p>
          {result ? (
            <><p className="mt-3 text-sm font-medium">{result.profileInputs.projectTitle}</p><p className="mt-2 text-xs leading-5 text-muted-foreground">{result.profileInputs.researchInterests.join(" · ")}</p></>
          ) : (
            <p className="mt-3 text-xs leading-5 text-muted-foreground">Matching uses the research interests, skills, and project saved in your account.</p>
          )}
        </div>
      </aside>
    </div>
  );
}
