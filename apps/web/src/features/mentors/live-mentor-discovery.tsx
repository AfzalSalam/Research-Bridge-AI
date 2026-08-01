"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
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
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";

import { DataState } from "@/components/states/data-state";
import { StatusBadge } from "@/components/status/status-badge";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { EvidenceLink } from "@/features/demo/components/evidence-link";
import { NativeSelect } from "@/features/demo/components/native-select";
import {
  liveMentorSearchFormSchema,
  type LiveMentorSearchForm,
  type LiveMentorSearchFormInput,
  type MentorCandidateResult,
  type MentorDiscoveryResponse,
} from "@/features/discovery/contracts";
import { discoverOpenAlexMentors } from "@/lib/api/mentors";
import { ApiError } from "@/lib/api/result";
import { cn } from "@/lib/utils";

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
          Evidence order · no prestige signal
        </p>
        <h2 className="mt-2 text-2xl font-medium" id="candidate-list-title">
          Researcher candidates
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
}: {
  candidate: MentorCandidateResult;
  onBack: () => void;
}) {
  return (
    <article>
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
      <Contributions candidate={candidate} />
      <Papers candidate={candidate} />
      <section className="mt-10 border-t-2 border-brand-indigo pt-7">
        <h3 className="text-xl font-medium">Evidence-grounded outreach is next</h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Phase 8 will use a human-selected researcher and papers to build an editable
          draft from verified facts only. It will not mass-send or invent an address.
        </p>
      </section>
    </article>
  );
}

function ResultWorkspace({ result }: { result: MentorDiscoveryResponse }) {
  const [selectedId, setSelectedId] = useState<string | null>(
    result.candidates[0]?.id ?? null,
  );
  const lastSelectedId = useRef<string | null>(selectedId);
  const selected = result.candidates.find((item) => item.id === selectedId);

  function selectCandidate(id: string) {
    lastSelectedId.current = id;
    setSelectedId(id);
  }

  function returnToCandidates() {
    setSelectedId(null);
    window.requestAnimationFrame(() => {
      if (lastSelectedId.current) {
        document.getElementById(`candidate-${lastSelectedId.current}`)?.focus();
      }
    });
  }
  return (
    <>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
        <div>
          <p className="text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">
            {result.policy.version} · transparent placement policy
          </p>
          <h2 className="mt-2 text-3xl font-medium">Reviewable researcher evidence</h2>
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
      <div className="grid gap-8 lg:grid-cols-[21rem_minmax(0,1fr)] lg:items-start lg:gap-10">
        <div className={cn(selected && "hidden lg:block", "lg:sticky lg:top-24")}>
          <CandidateList candidates={result.candidates} onSelect={selectCandidate} selectedId={selectedId} />
        </div>
        <div className={cn(!selected && "hidden lg:block")}>
          {selected ? (
            <CandidateDetail candidate={selected} key={selected.id} onBack={returnToCandidates} />
          ) : (
            <DataState description="Choose a candidate to inspect its evidence and uncertainty boundaries." kind="empty" title="Select a researcher" />
          )}
        </div>
      </div>
    </>
  );
}

export function LiveMentorDiscovery({ initialQuery }: { initialQuery?: string }) {
  const [activeController, setActiveController] = useState<AbortController | null>(null);
  const mutation = useMutation({ mutationFn: discoverOpenAlexMentors });
  const {
    formState: { errors },
    handleSubmit,
    register,
  } = useForm<LiveMentorSearchFormInput, unknown, LiveMentorSearchForm>({
    defaultValues: { query: initialQuery || fallbackQuery, paperLimit: 20 },
    resolver: zodResolver(liveMentorSearchFormSchema),
  });
  useEffect(() => () => activeController?.abort(), [activeController]);

  function submit(values: LiveMentorSearchForm) {
    activeController?.abort();
    const controller = new AbortController();
    setActiveController(controller);
    mutation.mutate({ ...values, candidateLimit: 12, signal: controller.signal });
  }

  const error = mutation.error instanceof ApiError ? mutation.error : null;
  const result = mutation.data;
  return (
    <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_20rem] xl:items-start">
      <section className="min-w-0">
        <form className="border border-border bg-surface p-5 sm:p-7" noValidate onSubmit={handleSubmit(submit)}>
          <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_9rem_auto] md:items-end">
            <Field data-invalid={Boolean(errors.query)}>
              <FieldLabel htmlFor="live-mentor-query">Research topic, DOI, or OpenAlex Work ID</FieldLabel>
              <Input aria-invalid={Boolean(errors.query)} id="live-mentor-query" placeholder="e.g. trustworthy ML for public health" {...register("query")} />
              <FieldError errors={[errors.query]} />
            </Field>
            <Field data-invalid={Boolean(errors.paperLimit)}>
              <FieldLabel htmlFor="live-mentor-paper-limit">Paper pool</FieldLabel>
              <NativeSelect id="live-mentor-paper-limit" {...register("paperLimit")}>
                <option value="10">10 papers</option>
                <option value="20">20 papers</option>
                <option value="25">25 papers</option>
              </NativeSelect>
              <FieldError errors={[errors.paperLimit]} />
            </Field>
            <Button disabled={mutation.isPending} type="submit" variant="evidence">
              <Search aria-hidden="true" /> {mutation.isPending ? "Deriving…" : "Find researchers"}
            </Button>
          </div>
          <FieldDescription className="mt-4 border-t border-border pt-4">
            OpenAlex supplies publication facts. Research Bridge applies a versioned
            deterministic policy—without an LLM, prestige signal, or invented score.
          </FieldDescription>
        </form>
        <div aria-live="polite" className="mt-8">
          {!mutation.isPending && !mutation.isError && !result ? (
            <DataState description="Search a focused topic to derive researchers from real publication authorships. Every connection exposes its evidence and unknowns." kind="empty" title="Ready to find paper-backed researchers" />
          ) : null}
          {mutation.isPending ? (
            <DataState description="Retrieving papers, consolidating repeated authors, calculating policy contributions, and checking evidence coverage." kind="loading" title="Building candidate evidence trails" />
          ) : null}
          {mutation.isError ? (
            <DataState
              action={mutation.variables ? <Button onClick={() => submit({ paperLimit: mutation.variables.paperLimit, query: mutation.variables.query })} variant="outline"><RefreshCw aria-hidden="true" /> Retry request</Button> : null}
              description={`${error?.message ?? "The researcher request could not be completed."}${error?.requestId ? ` Request reference: ${error.requestId}.` : ""}`}
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
      <aside className="border border-border bg-surface-subtle p-6 xl:sticky xl:top-24">
        <div className="grid size-10 place-items-center rounded-full bg-brand-teal-soft text-brand-teal-strong">
          <UserRoundSearch aria-hidden="true" className="size-5" />
        </div>
        <h2 className="mt-5 text-xl font-medium">What this proves</h2>
        <ul className="mt-4 space-y-4 text-sm leading-6 text-muted-foreground">
          <li className="flex gap-2"><Database aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Repeated authors collapse into one candidate with all supporting papers.</li>
          <li className="flex gap-2"><Scale aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Five documented features control ordering; an LLM cannot invent scores.</li>
          <li className="flex gap-2"><ShieldQuestion aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Title, current employer, contact, and openings stay unknown until verified.</li>
          <li className="flex gap-2"><FileSearch aria-hidden="true" className="mt-1 size-4 shrink-0 text-brand-teal" />Positive contributions retain paper evidence IDs.</li>
        </ul>
        <div className="mt-6 border-t border-border pt-5">
          <p className="text-xs font-bold tracking-[0.1em] text-muted-foreground uppercase">Profile context</p>
          {result ? (
            <><p className="mt-3 text-sm font-medium">{result.profileInputs.projectTitle}</p><p className="mt-2 text-xs leading-5 text-muted-foreground">{result.profileInputs.researchInterests.join(" · ")}</p></>
          ) : (
            <p className="mt-3 text-xs leading-5 text-muted-foreground">Your saved profile is used when available; otherwise a visibly fictional profile is the safe fallback.</p>
          )}
        </div>
      </aside>
    </div>
  );
}
