"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Bookmark,
  BookmarkCheck,
  CheckCircle2,
  ClipboardPlus,
  Database,
  MapPin,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
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
  opportunitySearchFormSchema,
  type OpportunityResult,
  type OpportunitySearchForm,
  type OpportunitySearchFormInput,
  type OpportunitySearchResponse,
} from "@/features/opportunities/contracts";
import { createLiveApplication } from "@/lib/api/applications";
import {
  listSavedLiveOpportunities,
  removeLiveOpportunity,
  saveLiveOpportunity,
  searchLiveOpportunities,
} from "@/lib/api/opportunities";
import { ApiError } from "@/lib/api/result";

const defaultValues: OpportunitySearchFormInput = {
  query: "machine learning",
  countryCode: "",
  workMode: "",
  funding: "",
  includeExpired: false,
  limit: 20,
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00.000Z`));
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

function displayValue(value: string): string {
  if (value === "unclear") return "Unclear";
  return value
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join("-");
}

function OpportunityCard({
  onSave,
  onTrack,
  opportunity,
  pendingAction,
}: {
  onSave: (opportunity: OpportunityResult) => void;
  onTrack: (opportunity: OpportunityResult) => void;
  opportunity: OpportunityResult;
  pendingAction: string | null;
}) {
  const isPending = pendingAction === opportunity.id;
  return (
    <article className="group relative flex min-w-0 flex-col overflow-hidden border border-border bg-surface shadow-[0_18px_60px_-48px_rgba(31,41,95,0.7)] transition-colors hover:border-brand-teal/40">
      <div className="h-1 bg-gradient-to-r from-brand-teal via-brand-teal to-brand-indigo" />
      <div className="flex flex-1 flex-col p-5 sm:p-7">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge tone="evidence">Official ATS</StatusBadge>
          <StatusBadge tone={opportunity.isExpired ? "error" : "evidence"}>
            {opportunity.isExpired ? "Expired" : "Published"}
          </StatusBadge>
          {opportunity.isStale ? (
            <StatusBadge tone="unknown">Verification stale</StatusBadge>
          ) : null}
        </div>

        <div className="mt-5">
          <p className="text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">
            {displayValue(opportunity.opportunityType)}
          </p>
          <h3 className="mt-2 text-2xl font-medium tracking-[-0.025em] text-balance">
            {opportunity.title}
          </h3>
          <p className="mt-2 text-sm font-semibold text-brand-teal-strong">
            {opportunity.organisation}
          </p>
          <p className="mt-1 flex items-start gap-2 text-sm leading-6 text-muted-foreground">
            <MapPin aria-hidden="true" className="mt-1 size-4 shrink-0" />
            {opportunity.location ?? "Location unclear"}
          </p>
        </div>

        <p className="mt-5 line-clamp-5 text-sm leading-7 text-foreground">
          {opportunity.descriptionExcerpt}
        </p>

        {opportunity.researchFields.length ? (
          <ul className="mt-5 flex flex-wrap gap-2" aria-label="Source departments">
            {opportunity.researchFields.map((field) => (
              <li
                className="rounded-full bg-brand-indigo-soft px-3 py-1 text-xs font-semibold text-brand-indigo"
                key={field}
              >
                {field}
              </li>
            ))}
          </ul>
        ) : null}

        <dl className="mt-6 grid grid-cols-2 gap-px overflow-hidden border border-border bg-border sm:grid-cols-4">
          {[
            ["Work mode", displayValue(opportunity.workMode)],
            ["Funding", displayValue(opportunity.funding)],
            ["Duration", opportunity.duration ?? "Unclear"],
            [
              "Deadline",
              opportunity.deadline ? formatDate(opportunity.deadline) : "Unclear",
            ],
          ].map(([label, value]) => (
            <div className="min-w-0 bg-surface-subtle p-3" key={label}>
              <dt className="text-[0.68rem] font-bold tracking-[0.09em] text-muted-foreground uppercase">
                {label}
              </dt>
              <dd className="mt-1 break-words text-sm font-semibold">{value}</dd>
            </div>
          ))}
        </dl>

        <details className="mt-5 border-t border-border pt-4">
          <summary className="cursor-pointer text-sm font-semibold text-foreground">
            Why this record is included
          </summary>
          <div className="mt-3 text-sm leading-6 text-muted-foreground">
            <p>
              Deterministic title signal: <strong>{opportunity.inclusionSignal}</strong>.
              No suitability score was calculated.
            </p>
            <p className="mt-2">
              Eligibility: {opportunity.eligibility ?? "Unclear — inspect the source."}
            </p>
            <ul className="mt-3 space-y-1">
              {opportunity.extractionEvidence.map((item) => (
                <li key={`${item.field}-${item.value}`}>
                  <span className="font-semibold text-foreground">{item.field}:</span>{" "}
                  {item.value}
                </li>
              ))}
            </ul>
          </div>
        </details>

        <div className="mt-auto border-t border-border pt-5">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs leading-5 text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <ShieldCheck aria-hidden="true" className="size-4 text-brand-teal" />
              Checked {formatDateTime(opportunity.lastVerifiedAt)}
            </span>
            <EvidenceLink href={opportunity.sourceUrl}>Inspect source record</EvidenceLink>
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <Button
              disabled={isPending}
              onClick={() => onSave(opportunity)}
              variant={opportunity.isSaved ? "evidence" : "outline"}
            >
              {opportunity.isSaved ? (
                <BookmarkCheck aria-hidden="true" />
              ) : (
                <Bookmark aria-hidden="true" />
              )}
              {opportunity.isSaved ? "Saved · remove" : "Save"}
            </Button>
            <Button
              disabled={!opportunity.isSaved || Boolean(opportunity.applicationId) || isPending}
              onClick={() => onTrack(opportunity)}
              variant="outline"
            >
              {opportunity.applicationId ? (
                <CheckCircle2 aria-hidden="true" />
              ) : (
                <ClipboardPlus aria-hidden="true" />
              )}
              {opportunity.applicationId ? "Tracked" : "Track"}
            </Button>
            <Button asChild variant="ghost">
              <a href={opportunity.applicationUrl} rel="noreferrer" target="_blank">
                {opportunity.isExpired ? "Inspect application" : "Official application"}
                <ArrowRight aria-hidden="true" />
                <span className="sr-only"> (opens in a new tab)</span>
              </a>
            </Button>
          </div>
          {opportunity.applicationId ? (
            <Button asChild className="mt-3 px-0" variant="link">
              <Link href="/applications">
                Open tracker <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
          ) : null}
        </div>
      </div>
    </article>
  );
}

export function LiveOpportunities() {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<OpportunitySearchResponse | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const searchMutation = useMutation({ mutationFn: searchLiveOpportunities });
  const saveMutation = useMutation({
    mutationFn: async (opportunity: OpportunityResult) => {
      if (opportunity.isSaved) {
        await removeLiveOpportunity({ opportunityId: opportunity.id });
        return { id: opportunity.id, isSaved: false };
      }
      await saveLiveOpportunity({ opportunityId: opportunity.id });
      return { id: opportunity.id, isSaved: true };
    },
  });
  const trackMutation = useMutation({ mutationFn: createLiveApplication });
  const savedQuery = useQuery({
    queryKey: ["opportunities", "saved"],
    queryFn: ({ signal }) => listSavedLiveOpportunities({ signal }),
  });
  const {
    formState: { errors },
    handleSubmit,
    register,
  } = useForm<OpportunitySearchFormInput, unknown, OpportunitySearchForm>({
    defaultValues,
    resolver: zodResolver(opportunitySearchFormSchema),
  });

  function submit(values: OpportunitySearchForm) {
    setResult(null);
    searchMutation.mutate(values, {
      onSuccess: (response) => {
        setResult(response);
        setAnnouncement(
          `${response.results.length} verified opportunity records are visible.`,
        );
      },
    });
  }

  function patchOpportunity(
    opportunityId: string,
    patch: Partial<OpportunityResult>,
  ) {
    setResult((current) =>
      current
        ? {
            ...current,
            results: current.results.map((item) =>
              item.id === opportunityId ? { ...item, ...patch } : item,
            ),
          }
        : current,
    );
  }

  function save(opportunity: OpportunityResult) {
    saveMutation.mutate(opportunity, {
      onSuccess: ({ id, isSaved }) => {
        patchOpportunity(id, { isSaved });
        setAnnouncement(
          isSaved
            ? "Opportunity saved to the durable workspace."
            : "Opportunity removed from saved items.",
        );
        void queryClient.invalidateQueries({ queryKey: ["opportunities", "saved"] });
      },
    });
  }

  function track(opportunity: OpportunityResult) {
    trackMutation.mutate(
      { opportunityId: opportunity.id },
      {
        onSuccess: (application) => {
          patchOpportunity(opportunity.id, { applicationId: application.id });
          setAnnouncement("Application added to the durable tracker at Saved.");
          void queryClient.invalidateQueries({ queryKey: ["applications"] });
        },
      },
    );
  }

  const searchError =
    searchMutation.error instanceof ApiError ? searchMutation.error : null;
  const actionError =
    saveMutation.error instanceof ApiError
      ? saveMutation.error
      : trackMutation.error instanceof ApiError
        ? trackMutation.error
        : null;
  const allSourcesFailed =
    result !== null && result.sources.every((source) => source.status === "error");
  const pendingAction = saveMutation.isPending
    ? saveMutation.variables.id
    : trackMutation.isPending
      ? trackMutation.variables.opportunityId
      : null;

  return (
    <div>
      <section
        className="overflow-hidden border border-border bg-surface"
        aria-labelledby="live-opportunity-search"
      >
        <div className="grid gap-6 border-b border-border bg-[linear-gradient(115deg,var(--brand-teal-soft),transparent_52%,var(--brand-indigo-soft))] p-5 sm:p-7 lg:grid-cols-[minmax(0,1fr)_18rem] lg:items-end">
          <div>
            <div className="flex items-center gap-3">
              <div className="grid size-10 place-items-center rounded-full bg-brand-teal text-white">
                <Search aria-hidden="true" className="size-5" />
              </div>
              <div>
                <p className="text-xs font-bold tracking-[0.12em] text-brand-teal-strong uppercase">
                  Live controlled source
                </p>
                <h2 className="mt-1 text-2xl font-medium" id="live-opportunity-search">
                  Search employer-published research openings
                </h2>
              </div>
            </div>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-muted-foreground">
              Research Bridge reads public Greenhouse GET feeds from a small allowlist,
              keeps unknown facts unclear, and links every record to the official application.
            </p>
          </div>
          <div className="border border-brand-indigo/15 bg-surface/80 p-4">
            <p className="text-xs font-bold tracking-[0.1em] text-brand-indigo uppercase">
              Durable workspace
            </p>
            <p className="mt-2 text-2xl font-medium">
              {savedQuery.isError
                ? "Unavailable"
                : savedQuery.isSuccess
                  ? savedQuery.data.length
                  : "—"}
            </p>
            <p className="text-sm text-muted-foreground">
              {savedQuery.isError
                ? "saved count could not be loaded"
                : "saved live opportunities"}
            </p>
          </div>
        </div>

        <form className="p-5 sm:p-7" noValidate onSubmit={handleSubmit(submit)}>
          <div className="grid gap-5 lg:grid-cols-[minmax(15rem,1fr)_7rem_10rem_10rem_7rem_auto] lg:items-end">
            <Field data-invalid={Boolean(errors.query)}>
              <FieldLabel htmlFor="live-opportunity-query">Research topic</FieldLabel>
              <Input
                aria-invalid={Boolean(errors.query)}
                id="live-opportunity-query"
                placeholder="e.g. machine learning robotics"
                {...register("query")}
              />
              <FieldError errors={[errors.query]} />
            </Field>
            <Field data-invalid={Boolean(errors.countryCode)}>
              <FieldLabel htmlFor="opportunity-country">Country</FieldLabel>
              <Input
                aria-invalid={Boolean(errors.countryCode)}
                id="opportunity-country"
                maxLength={2}
                placeholder="Any"
                {...register("countryCode")}
              />
              <FieldError errors={[errors.countryCode]} />
            </Field>
            <Field>
              <FieldLabel htmlFor="opportunity-mode">Work mode</FieldLabel>
              <NativeSelect id="opportunity-mode" {...register("workMode")}>
                <option value="">Any mode</option>
                <option value="on-site">On-site</option>
                <option value="hybrid">Hybrid</option>
                <option value="remote">Remote</option>
                <option value="unclear">Unclear</option>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="opportunity-funding">Funding</FieldLabel>
              <NativeSelect id="opportunity-funding" {...register("funding")}>
                <option value="">Any funding</option>
                <option value="funded">Funded</option>
                <option value="unfunded">Unfunded</option>
                <option value="unclear">Unclear</option>
              </NativeSelect>
            </Field>
            <Field>
              <FieldLabel htmlFor="opportunity-limit">Limit</FieldLabel>
              <NativeSelect id="opportunity-limit" {...register("limit")}>
                <option value="10">10</option>
                <option value="20">20</option>
                <option value="30">30</option>
              </NativeSelect>
            </Field>
            <Button disabled={searchMutation.isPending} type="submit" variant="evidence">
              <Search aria-hidden="true" />
              {searchMutation.isPending ? "Checking…" : "Search"}
            </Button>
          </div>
          <label className="mt-5 flex min-h-11 cursor-pointer items-center gap-3 text-sm text-muted-foreground">
            <input
              className="size-5 accent-[var(--brand-teal)]"
              type="checkbox"
              {...register("includeExpired")}
            />
            Include records with an explicit past deadline
          </label>
          <FieldDescription className="mt-4 border-t border-border pt-4">
            Results use freshness-first provider order after deterministic filtering.
            No ranking or selection score is applied.
          </FieldDescription>
        </form>
      </section>

      <p aria-live="polite" className="sr-only">{announcement}</p>

      {actionError ? (
        <div
          className="mt-6 border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
          role="alert"
        >
          {actionError.message}
          {actionError.requestId ? ` Reference: ${actionError.requestId}.` : ""}
        </div>
      ) : null}

      <div className="mt-8" aria-live="polite">
        {!result && !searchMutation.isPending && !searchMutation.isError ? (
          <DataState
            description="Search a focused topic. The backend inspects only configured public employer feeds and never crawls arbitrary university pages."
            kind="empty"
            title="Ready to check verified opportunity sources"
          />
        ) : null}
        {searchMutation.isPending ? (
          <DataState
            description="The server is checking allowlisted boards, validating records, sanitizing source text, and writing provenance."
            kind="loading"
            title="Verifying published opportunities"
          />
        ) : null}
        {searchMutation.isError ? (
          <DataState
            action={
              <Button onClick={() => searchMutation.reset()} variant="outline">
                <RefreshCw aria-hidden="true" />Reset search
              </Button>
            }
            description={`${searchError?.message ?? "The live search could not be completed."}${searchError?.requestId ? ` Reference: ${searchError.requestId}.` : ""}`}
            kind="error"
            title="Opportunity search is unavailable"
          />
        ) : null}
        {!searchMutation.isPending && result && allSourcesFailed ? (
          <DataState
            description="Every configured source failed this request. No cached record is presented as fresh; retry when the providers are available."
            kind="error"
            title="Verified sources are unavailable"
          />
        ) : null}
        {!searchMutation.isPending && result?.partialFailure && !allSourcesFailed ? (
          <DataState
            className="mb-6 min-h-0"
            description={`${result.sources.filter((source) => source.status === "error").length} source request failed. Results from successful sources keep their own verification times.`}
            kind="partial"
            title="Some allowlisted sources did not respond"
          />
        ) : null}
        {!searchMutation.isPending &&
        result &&
        !allSourcesFailed &&
        result.results.length === 0 ? (
          <DataState
            description="No admitted internship, studentship, fellowship, or research assistantship matched this topic and filter set. Broaden the topic or remove a filter."
            kind="empty"
            title="No verified opportunity matched"
          />
        ) : null}
        {!searchMutation.isPending &&
        result &&
        !allSourcesFailed &&
        result.results.length ? (
          <section aria-labelledby="live-opportunity-results">
            <div className="grid gap-5 border-y border-border py-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
              <div>
                <p className="flex items-center gap-2 text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">
                  <Database aria-hidden="true" className="size-4" />
                  {result.policyVersion} · no ranking
                </p>
                <h2 className="mt-2 text-3xl font-medium" id="live-opportunity-results">
                  {result.results.length} source-linked opening
                  {result.results.length === 1 ? "" : "s"}
                </h2>
              </div>
              <p className="text-sm text-muted-foreground">
                Checked {formatDateTime(result.retrievedAt)}
              </p>
            </div>
            <div className="grid gap-6 pt-6 xl:grid-cols-2">
              {result.results.map((opportunity) => (
                <OpportunityCard
                  key={opportunity.id}
                  onSave={save}
                  onTrack={track}
                  opportunity={opportunity}
                  pendingAction={pendingAction}
                />
              ))}
            </div>
            <aside
              className="mt-8 grid gap-4 border border-border bg-surface-subtle p-5 sm:grid-cols-2 lg:grid-cols-4"
              aria-label="Source health"
            >
              {result.sources.map((source) => (
                <div key={source.key}>
                  <StatusBadge
                    tone={source.status === "success" ? "evidence" : "unknown"}
                  >
                    {source.status === "success" ? "Checked" : "Unavailable"}
                  </StatusBadge>
                  <p className="mt-2 text-sm font-semibold">{source.organisation}</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {source.status === "success"
                      ? `${source.acceptedCount} admitted title signal${source.acceptedCount === 1 ? "" : "s"}`
                      : source.errorCode ?? "Provider error"}
                  </p>
                </div>
              ))}
            </aside>
          </section>
        ) : null}
      </div>
    </div>
  );
}
