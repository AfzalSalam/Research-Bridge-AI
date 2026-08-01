"use client";

import { useMutation } from "@tanstack/react-query";
import {
  Check,
  Clipboard,
  FileCheck2,
  FilePenLine,
  RefreshCw,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DataState } from "@/components/states/data-state";
import { StatusBadge } from "@/components/status/status-badge";
import { EvidenceLink } from "@/features/demo/components/evidence-link";
import type { MentorCandidateResult } from "@/features/discovery/contracts";
import type { OutreachDraftResponse } from "@/features/outreach/contracts";
import {
  createLiveOutreachDraft,
  getLiveOutreachDraft,
  updateLiveOutreachDraft,
} from "@/lib/api/outreach";
import { ApiError } from "@/lib/api/result";

const fallbackLabels: Record<
  NonNullable<OutreachDraftResponse["generation"]["fallbackReason"]>,
  string
> = {
  "deterministic-requested": "Deterministic mode requested",
  "provider-not-configured": "Model key not configured",
  "provider-unavailable": "Model provider unavailable",
  "provider-refused": "Model declined the request",
  "invalid-provider-output": "Model output failed validation",
  "grounding-check-failed": "Model output failed grounding review",
};

function SelectionStep({
  candidate,
  onChange,
  pending,
  selectedIds,
}: {
  candidate: MentorCandidateResult;
  onChange: (paperId: string, checked: boolean) => void;
  pending: boolean;
  selectedIds: string[];
}) {
  return (
    <fieldset>
      <legend className="text-base font-semibold">1. Select one or two papers</legend>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Only checked papers may influence the customized draft. Publication evidence
        is revalidated on the server.
      </p>
      <div className="mt-4 divide-y divide-border border-y border-border">
        {candidate.supportingPapers.map((paper) => {
          const checked = selectedIds.includes(paper.id);
          const atLimit = selectedIds.length >= 2 && !checked;
          return (
            <label
              className="flex min-h-16 cursor-pointer items-start gap-3 py-4 has-disabled:cursor-not-allowed has-disabled:opacity-55"
              key={paper.id}
            >
              <input
                checked={checked}
                className="mt-1 size-5 shrink-0 accent-[var(--brand-teal)]"
                disabled={pending || atLimit}
                name="outreach-paper"
                onChange={(event) => onChange(paper.id, event.target.checked)}
                type="checkbox"
              />
              <span className="min-w-0">
                <span className="block font-medium leading-6">{paper.title}</span>
                <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                  {paper.publicationYear} · {paper.venue ?? "Venue unknown"} ·{" "}
                  {paper.evidenceStrength === "full-abstract"
                    ? "validated abstract"
                    : "title-only evidence"}
                </span>
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function EvidenceInspector({ draft }: { draft: OutreachDraftResponse }) {
  return (
    <aside className="border border-border bg-surface-subtle p-5 sm:p-6">
      <div className="flex flex-wrap gap-2">
        <StatusBadge tone="evidence">
          {draft.generation.mode === "llm" ? "Structured LLM" : "Deterministic"}
        </StatusBadge>
        <StatusBadge>Version {draft.draftVersion}</StatusBadge>
        <StatusBadge
          tone={
            draft.evidenceMapStatus === "verified-generated" ? "evidence" : "unknown"
          }
        >
          {draft.evidenceMapStatus === "verified-generated"
            ? "Generated map verified"
            : "Edited map needs review"}
        </StatusBadge>
      </div>
      <h4 className="mt-5 text-lg font-medium">Claim-to-evidence map</h4>
      <ol className="mt-4 space-y-5">
        {draft.claimEvidence.map((item, index) => (
          <li className="border-l-2 border-brand-teal pl-4" key={`${item.claim}-${index}`}>
            <p className="text-sm leading-6">{item.claim}</p>
            <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
              {item.references.map((reference) => (
                <li className="text-xs text-muted-foreground" key={`${reference.type}-${reference.id}`}>
                  {reference.sourceUrl ? (
                    <EvidenceLink href={reference.sourceUrl}>{reference.label}</EvidenceLink>
                  ) : (
                    `Profile · ${reference.label}`
                  )}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
      <div className="mt-6 border-t border-border pt-5">
        <p className="text-xs font-bold tracking-[0.1em] text-muted-foreground uppercase">
          Generation provenance
        </p>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {draft.generation.provider && draft.generation.model
            ? `${draft.generation.provider} · ${draft.generation.model} · ${draft.generation.promptVersion}`
            : `${draft.generation.templateVersion} · ${
                draft.generation.fallbackReason
                  ? fallbackLabels[draft.generation.fallbackReason]
                  : "Deterministic template"
              }`}
        </p>
      </div>
    </aside>
  );
}

function DraftEditor({
  draft,
  onDraftChange,
}: {
  draft: OutreachDraftResponse;
  onDraftChange: (draft: OutreachDraftResponse) => void;
}) {
  const [subject, setSubject] = useState(draft.subject);
  const [body, setBody] = useState(draft.body);
  const [reviewed, setReviewed] = useState(false);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const saveMutation = useMutation({ mutationFn: updateLiveOutreachDraft });
  const refreshMutation = useMutation({ mutationFn: getLiveOutreachDraft });
  const hasChanges = subject !== draft.subject || body !== draft.body;
  const contentIsValid = subject.trim().length >= 5 && body.trim().length >= 80;
  const editorPending = saveMutation.isPending || refreshMutation.isPending;

  function markChanged() {
    setReviewed(false);
    setCopyStatus("idle");
  }

  function reloadLatest() {
    refreshMutation.mutate(
      { draftId: draft.id },
      {
        onSuccess: (latest) => {
          onDraftChange(latest);
          setSubject(latest.subject);
          setBody(latest.body);
          setReviewed(false);
          setCopyStatus("idle");
          saveMutation.reset();
        },
      },
    );
  }

  function save() {
    saveMutation.mutate(
      {
        body,
        draftId: draft.id,
        expectedVersion: draft.draftVersion,
        subject,
      },
      {
        onSuccess: (saved) => {
          onDraftChange(saved);
          setSubject(saved.subject);
          setBody(saved.body);
          setReviewed(false);
        },
      },
    );
  }

  async function copyDraft() {
    try {
      await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("failed");
    }
  }

  const saveError = saveMutation.error instanceof ApiError ? saveMutation.error : null;
  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_21rem]">
      <section className="min-w-0 border border-border bg-surface p-5 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">
              3. Edit, save, review
            </p>
            <h3 className="mt-2 text-2xl font-medium">Outreach draft</h3>
          </div>
          {hasChanges ? (
            <StatusBadge tone="unknown">Unsaved edits</StatusBadge>
          ) : (
            <StatusBadge tone="evidence">Saved version {draft.draftVersion}</StatusBadge>
          )}
        </div>
        <div className="mt-6 space-y-5">
          <div>
            <label className="text-sm font-semibold" htmlFor={`draft-subject-${draft.id}`}>
              Subject
            </label>
            <Input
              className="mt-2"
              disabled={editorPending}
              id={`draft-subject-${draft.id}`}
              maxLength={160}
              onChange={(event) => {
                setSubject(event.target.value);
                markChanged();
              }}
              value={subject}
            />
          </div>
          <div>
            <label className="text-sm font-semibold" htmlFor={`draft-body-${draft.id}`}>
              Email body
            </label>
            <Textarea
              className="mt-2 min-h-96 leading-7"
              disabled={editorPending}
              id={`draft-body-${draft.id}`}
              maxLength={5000}
              onChange={(event) => {
                setBody(event.target.value);
                markChanged();
              }}
              value={body}
            />
          </div>
        </div>
        {saveMutation.isError || refreshMutation.isError ? (
          <div className="mt-4 text-sm text-destructive" role="alert">
            <p>
              {refreshMutation.isError
                ? "The latest saved draft could not be loaded."
                : (saveError?.message ?? "The edited draft could not be saved.")}
            </p>
            {saveError?.code === "draft_version_conflict" ? (
              <Button
                className="mt-3"
                disabled={refreshMutation.isPending}
                onClick={reloadLatest}
                size="sm"
                variant="outline"
              >
                <RefreshCw aria-hidden="true" />
                {refreshMutation.isPending ? "Loading latest…" : "Load latest version"}
              </Button>
            ) : null}
          </div>
        ) : null}
        <div className="mt-6 flex flex-wrap gap-3 border-t border-border pt-5">
          <Button
            disabled={!hasChanges || !contentIsValid || editorPending}
            onClick={save}
            variant="evidence"
          >
            <FilePenLine aria-hidden="true" />
            {saveMutation.isPending ? "Saving…" : "Save new version"}
          </Button>
        </div>
        <div className="mt-7 border border-warning/30 bg-warning-soft p-4">
          <label className="flex cursor-pointer items-start gap-3 text-sm leading-6">
            <input
              checked={reviewed}
              className="mt-1 size-5 shrink-0 accent-[var(--brand-indigo)]"
              disabled={hasChanges || editorPending}
              onChange={(event) => {
                setReviewed(event.target.checked);
                setCopyStatus("idle");
              }}
              type="checkbox"
            />
            <span>
              I reviewed the current saved subject and body against the evidence and
              will verify the recipient on an official source before using it.
            </span>
          </label>
          <Button
            className="mt-4"
            disabled={!reviewed || hasChanges || editorPending}
            onClick={copyDraft}
            variant="outline"
          >
            {copyStatus === "copied" ? <Check aria-hidden="true" /> : <Clipboard aria-hidden="true" />}
            {copyStatus === "copied" ? "Copied for your review" : "Copy reviewed draft"}
          </Button>
          <p aria-live="polite" className="mt-2 text-xs text-muted-foreground">
            {copyStatus === "failed"
              ? "Clipboard access failed. Select the text manually."
              : "Copying is not sending; Research Bridge AI has no email transport."}
          </p>
        </div>
      </section>
      <EvidenceInspector draft={draft} />
    </div>
  );
}

export function LiveOutreachWorkspace({
  candidate,
  query,
}: {
  candidate: MentorCandidateResult;
  query: string;
}) {
  const [selectedIds, setSelectedIds] = useState<string[]>([
    candidate.supportingPapers[0]?.id ?? "",
  ].filter(Boolean));
  const [preference, setPreference] = useState<"auto" | "deterministic">("auto");
  const [draft, setDraft] = useState<OutreachDraftResponse | null>(null);
  const mutation = useMutation({ mutationFn: createLiveOutreachDraft });
  const selectedPapers = useMemo(
    () => candidate.supportingPapers.filter((paper) => selectedIds.includes(paper.id)),
    [candidate.supportingPapers, selectedIds],
  );

  function changePaper(paperId: string, checked: boolean) {
    setSelectedIds((current) =>
      checked
        ? current.length < 2
          ? [...current, paperId]
          : current
        : current.filter((id) => id !== paperId),
    );
    setDraft(null);
    mutation.reset();
  }

  function generate() {
    mutation.mutate(
      {
        generationPreference: preference,
        mentorId: candidate.id,
        paperIds: selectedIds,
        query,
      },
      { onSuccess: setDraft },
    );
  }

  const error = mutation.error instanceof ApiError ? mutation.error : null;
  return (
    <section className="mt-12 border-t-2 border-brand-indigo pt-8" aria-labelledby="outreach-title">
      <div className="flex items-start gap-3">
        <div className="grid size-10 shrink-0 place-items-center rounded-full bg-brand-indigo-soft text-brand-indigo">
          <Sparkles aria-hidden="true" className="size-5" />
        </div>
        <div>
          <p className="text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">
            Human-selected outreach
          </p>
          <h3 className="mt-1 text-2xl font-medium" id="outreach-title">
            Write from evidence, then make it yours
          </h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            Recipient contact, title, current institution, availability, and funding
            remain unknown. This workspace drafts and copies; it never sends.
          </p>
        </div>
      </div>

      <div className="mt-7 border border-border bg-surface p-5 sm:p-7">
        <SelectionStep
          candidate={candidate}
          onChange={changePaper}
          pending={mutation.isPending}
          selectedIds={selectedIds}
        />
        <div className="mt-7 grid gap-5 border-t border-border pt-6 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
          <div>
            <label className="text-base font-semibold" htmlFor={`generation-${candidate.id}`}>
              2. Choose generation mode
            </label>
            <select
              className="mt-2 h-11 w-full rounded-md border border-input bg-surface px-3.5 text-base outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20"
              id={`generation-${candidate.id}`}
              disabled={mutation.isPending}
              onChange={(event) => {
                setPreference(event.target.value as "auto" | "deterministic");
                setDraft(null);
                mutation.reset();
              }}
              value={preference}
            >
              <option value="auto">Best available · model with safe fallback</option>
              <option value="deterministic">Deterministic template only</option>
            </select>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">
              {selectedPapers.length} paper{selectedPapers.length === 1 ? "" : "s"} selected.
              The server reconstructs every fact from stored evidence.
            </p>
          </div>
          <Button
            disabled={selectedIds.length === 0 || mutation.isPending}
            onClick={generate}
            variant="evidence"
          >
            <FileCheck2 aria-hidden="true" />
            {mutation.isPending ? "Grounding draft…" : "Build grounded draft"}
          </Button>
        </div>
      </div>

      <div aria-live="polite" className="mt-7">
        {mutation.isPending ? (
          <DataState
            description="Revalidating the selected researcher and papers, composing bounded prose, checking references, and persisting version 1."
            kind="loading"
            title="Building an evidence-grounded draft"
          />
        ) : null}
        {mutation.isError ? (
          <DataState
            action={
              <Button onClick={generate} variant="outline">
                <RefreshCw aria-hidden="true" /> Retry draft
              </Button>
            }
            description={`${error?.message ?? "The draft could not be created."}${
              error?.requestId ? ` Request reference: ${error.requestId}.` : ""
            }`}
            kind="error"
            title="Outreach draft is unavailable"
          />
        ) : null}
        {draft ? <DraftEditor draft={draft} onDraftChange={setDraft} /> : null}
        {!draft && !mutation.isPending && !mutation.isError ? (
          <div className="flex gap-3 border-l-2 border-warning bg-warning-soft p-4 text-sm leading-6 text-warning-foreground">
            <ShieldAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
            Select evidence and generate a draft. Title-only papers are always
            described cautiously, even when a model is configured.
          </div>
        ) : null}
      </div>
    </section>
  );
}
