"use client";

import { useMutation } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  ClipboardCheck,
  Copy,
  FileText,
  Mail,
  Save,
  ShieldAlert,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { DataState } from "@/components/states/data-state";
import { StatusBadge } from "@/components/status/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { DemoDataBoundary } from "@/features/demo/components/demo-data-boundary";
import { EvidenceLink } from "@/features/demo/components/evidence-link";
import { FactRow } from "@/features/demo/components/fact-row";
import {
  applicationSchema,
  outreachDraftSchema,
  type MentorCandidate,
} from "@/features/demo/contracts";
import { useReadyDemoStore } from "@/features/demo/demo-store";
import { createDemoOutreachDraft, DemoApiError } from "@/lib/api/demo";
import { cn } from "@/lib/utils";

function MentorList({
  mentors,
  onSelect,
  selectedMentorId,
}: {
  mentors: MentorCandidate[];
  onSelect: (mentorId: string) => void;
  selectedMentorId: string | null;
}) {
  return (
    <section aria-labelledby="mentor-list-title">
      <div className="border-b border-border pb-4">
        <p className="text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">
          Demo order · not ranked
        </p>
        <h2 className="mt-2 text-2xl font-medium" id="mentor-list-title">
          Fictional researcher candidates
        </h2>
      </div>
      <div className="divide-y divide-border border-b border-border">
        {mentors.map((mentor) => {
          const selected = mentor.id === selectedMentorId;
          return (
            <button
              aria-pressed={selected}
              className={cn(
                "block w-full border-l-2 px-4 py-5 text-left transition-colors hover:bg-muted/70 focus-visible:outline-offset-[-3px] motion-reduce:transition-none",
                selected
                  ? "border-l-brand-teal bg-brand-teal-soft/55"
                  : "border-l-transparent bg-surface",
              )}
              key={mentor.id}
              onClick={() => onSelect(mentor.id)}
              type="button"
            >
              <span className="flex flex-wrap gap-2">
                <StatusBadge tone="evidence">
                  {mentor.papers.length} {mentor.papers.length === 1 ? "source" : "sources"}
                </StatusBadge>
                <StatusBadge tone="unknown">Openings unknown</StatusBadge>
              </span>
              <span className="mt-3 block font-serif text-xl font-medium text-foreground">
                {mentor.name}
              </span>
              <span className="mt-1 block text-sm leading-6 text-muted-foreground">
                {mentor.department} · {mentor.institution}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function DraftWorkspace({ mentor }: { mentor: MentorCandidate }) {
  const { dispatch, state } = useReadyDemoStore();
  const selectedPaperIds = state.selectedPaperIds[mentor.id] ?? [];
  const savedDraft = state.drafts.find((draft) => draft.mentorId === mentor.id);
  const isTracked = state.applications.some(
    (application) =>
      application.targetType === "mentor" && application.targetId === mentor.id,
  );
  const [subject, setSubject] = useState(savedDraft?.subject ?? "");
  const [body, setBody] = useState(savedDraft?.body ?? "");
  const [announcement, setAnnouncement] = useState("");
  const draftMutation = useMutation({
    mutationFn: createDemoOutreachDraft,
    onSuccess: (draft) => {
      dispatch({ type: "save-draft", draft });
      setSubject(draft.subject);
      setBody(draft.body);
      setAnnouncement(
        "Editable deterministic draft created by the mock API from the selected evidence.",
      );
    },
    onError: (error) => {
      const apiError =
        error instanceof DemoApiError
          ? error
          : new DemoApiError({
              code: "unexpected_client_error",
              message: "The draft request could not be completed.",
            });
      const requestReference = apiError.requestId
        ? ` Request reference: ${apiError.requestId}.`
        : "";
      setAnnouncement(`${apiError.message}${requestReference}`);
    },
  });

  const selectedPapers = mentor.papers.filter((paper) =>
    selectedPaperIds.includes(paper.id),
  );

  function createDraft() {
    draftMutation.mutate({
      mentorId: mentor.id,
      paperIds: selectedPapers.map((paper) => paper.id),
      profile: state.profile,
    });
  }

  function saveDraft() {
    if (!savedDraft) return;
    const result = outreachDraftSchema.safeParse({
      ...savedDraft,
      body,
      subject,
      updatedAt: new Date().toISOString(),
    });
    if (!result.success) {
      setAnnouncement(
        "Keep a subject of 5-160 characters and an email body of at least 80 characters.",
      );
      return;
    }
    dispatch({ type: "save-draft", draft: result.data });
    setAnnouncement("Draft edits saved in this browser session.");
  }

  async function copyDraft() {
    try {
      await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
      setAnnouncement("Draft copied. Review it before using it anywhere else.");
    } catch {
      setAnnouncement("Copy was blocked by the browser. Select the draft text manually.");
    }
  }

  function trackDraft() {
    if (!savedDraft) return;
    const changedAt = new Date().toISOString();
    dispatch({
      type: "track-application",
      application: applicationSchema.parse({
        id: `application-${mentor.id}`,
        targetType: "mentor",
        targetId: mentor.id,
        targetLabel: mentor.name,
        sourceUrl: mentor.sourceUrl,
        status: "Ready for review",
        notes: "Evidence-grounded outreach draft prepared; not sent.",
        followUpDate: null,
        updatedAt: changedAt,
        history: [{ status: "Ready for review", changedAt }],
      }),
    });
    setAnnouncement("Draft added to the tracker as Ready for review. Nothing was sent.");
  }

  return (
    <section className="mt-10 border-t-2 border-brand-indigo pt-8" aria-labelledby="draft-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <p className="text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">
            Human approval boundary
          </p>
          <h2 className="mt-2 text-3xl font-medium" id="draft-title">
            Custom outreach draft
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Select at least one paper. The mock API template uses only profile facts
            and the selected evidence; it does not infer an email address or send
            anything.
          </p>
        </div>
        <StatusBadge tone={savedDraft ? "evidence" : "neutral"}>
          {savedDraft ? "Editable draft ready" : "Evidence required"}
        </StatusBadge>
      </div>

      <fieldset className="mt-6">
        <legend className="text-sm font-bold">Choose paper evidence for the email</legend>
        <div className="mt-3 grid gap-3">
          {mentor.papers.map((paper) => {
            const checked = selectedPaperIds.includes(paper.id);
            return (
              <label
                className={cn(
                  "grid cursor-pointer grid-cols-[1.25rem_minmax(0,1fr)] gap-3 border p-4 transition-colors motion-reduce:transition-none",
                  checked
                    ? "border-brand-teal/40 bg-brand-teal-soft/50"
                    : "border-border bg-surface hover:bg-muted/50",
                )}
                key={paper.id}
              >
                <input
                  checked={checked}
                  className="mt-1 size-4 accent-[var(--brand-teal)]"
                  onChange={() =>
                    dispatch({ type: "toggle-paper", mentorId: mentor.id, paperId: paper.id })
                  }
                  type="checkbox"
                />
                <span>
                  <span className="block font-semibold text-foreground">{paper.title}</span>
                  <span className="mt-1 block text-sm leading-6 text-muted-foreground">
                    {paper.year} · {paper.venue} · {paper.evidenceStrength === "title-only" ? "title metadata only" : "fictional abstract available"}
                  </span>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <div className="mt-5 flex flex-wrap items-center gap-4">
        <Button
          disabled={selectedPapers.length === 0 || draftMutation.isPending}
          onClick={createDraft}
          variant="evidence"
        >
          <Mail aria-hidden="true" />
          {draftMutation.isPending
            ? "Creating draft…"
            : savedDraft
              ? "Rebuild from selected evidence"
              : "Create editable draft"}
        </Button>
        {selectedPapers.some((paper) => paper.evidenceStrength === "title-only") ? (
          <p className="flex max-w-xl gap-2 text-sm leading-6 text-warning-foreground">
            <ShieldAlert aria-hidden="true" className="mt-1 size-4 shrink-0" />
            Title-only evidence will produce a cautious reference and no technical claim.
          </p>
        ) : null}
      </div>

      {savedDraft ? (
        <div className="mt-8 border border-border bg-surface-subtle p-5 sm:p-7">
          <div className="grid gap-5">
            <div>
              <Label htmlFor="draft-subject">Subject</Label>
              <Input
                className="mt-2 bg-surface"
                id="draft-subject"
                onChange={(event) => setSubject(event.target.value)}
                value={subject}
              />
            </div>
            <div>
              <Label htmlFor="draft-body">Email body</Label>
              <Textarea
                className="mt-2 min-h-96 bg-surface"
                id="draft-body"
                onChange={(event) => setBody(event.target.value)}
                value={body}
              />
            </div>
          </div>

          <div className="mt-6 border-l-2 border-brand-indigo bg-brand-indigo-soft/55 p-4">
            <p className="text-sm font-bold text-foreground">Draft provenance</p>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Mode: deterministic demo · Template: {savedDraft.templateVersion} · No LLM
              or email provider was called.
            </p>
            <ul className="mt-3 space-y-1 text-sm leading-6 text-warning-foreground">
              {savedDraft.uncertaintyWarnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
              {savedDraft.evidenceLinks.map((link, index) => (
                <EvidenceLink href={link} key={link}>
                  Evidence {index + 1}
                </EvidenceLink>
              ))}
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <Button onClick={saveDraft} variant="evidence">
              <Save aria-hidden="true" />
              Save edits
            </Button>
            <Button onClick={copyDraft} variant="outline">
              <Copy aria-hidden="true" />
              Copy for review
            </Button>
            <Button disabled={isTracked} onClick={trackDraft} variant="outline">
              <ClipboardCheck aria-hidden="true" />
              {isTracked ? "Added to tracker" : "Add to tracker"}
            </Button>
            <Button asChild variant="link">
              <Link href="/applications">Open tracker</Link>
            </Button>
          </div>
          <p aria-live="polite" className="mt-4 text-sm text-muted-foreground">
            {announcement || "Review and edit every sentence before using this draft."}
          </p>
        </div>
      ) : null}
    </section>
  );
}

function MentorDetail({ mentor, onBack }: { mentor: MentorCandidate; onBack: () => void }) {
  return (
    <article>
      <Button className="mb-5 lg:hidden" onClick={onBack} size="sm" variant="outline">
        <ArrowLeft aria-hidden="true" />
        Back to candidates
      </Button>

      <div className="flex flex-wrap gap-2">
        <StatusBadge tone="evidence">Publication evidence available</StatusBadge>
        <StatusBadge tone="unknown">Contact unknown</StatusBadge>
        <StatusBadge tone="unknown">Funding unknown</StatusBadge>
      </div>
      <h2 className="mt-5 text-4xl font-medium tracking-[-0.03em]">{mentor.name}</h2>
      <p className="mt-2 text-base leading-7 text-muted-foreground">
        {mentor.role}, {mentor.department}
      </p>

      <dl className="mt-7 border-y border-border">
        <FactRow label="Institution" value={mentor.institution} />
        <FactRow label="Location" value={mentor.location} />
        <FactRow label="Identity" value={mentor.identityNote} />
        <FactRow label="Profile source" value={<EvidenceLink href={mentor.sourceUrl} />} />
      </dl>

      <section className="mt-8" aria-labelledby="connection-title">
        <h3 className="text-2xl font-medium" id="connection-title">
          Why this connection is shown
        </h3>
        <ul className="mt-4 grid gap-3">
          {mentor.fitRationale.map((reason) => (
            <li className="grid grid-cols-[1.25rem_minmax(0,1fr)] gap-3 text-sm leading-6" key={reason}>
              <CheckCircle2 aria-hidden="true" className="mt-1 size-4 text-brand-teal" />
              {reason}
            </li>
          ))}
        </ul>
        <p className="mt-4 border-l-2 border-warning bg-warning-soft p-4 text-sm leading-6 text-warning-foreground">
          This explanation describes observable overlap only. It is not a ranking score,
          endorsement, or claim that the researcher is accepting students.
        </p>
      </section>

      <section className="mt-9" aria-labelledby="papers-title">
        <div className="flex items-center gap-3">
          <FileText aria-hidden="true" className="size-5 text-brand-indigo" />
          <h3 className="text-2xl font-medium" id="papers-title">
            Paper evidence
          </h3>
        </div>
        <div className="mt-4 divide-y divide-border border-y border-border">
          {mentor.papers.map((paper) => (
            <article className="py-6" key={paper.id}>
              <div className="flex flex-wrap gap-2">
                <StatusBadge tone="evidence">{paper.year}</StatusBadge>
                <StatusBadge tone={paper.evidenceStrength === "title-only" ? "unknown" : "neutral"}>
                  {paper.evidenceStrength === "title-only" ? "Title metadata only" : "Fictional abstract"}
                </StatusBadge>
              </div>
              <h4 className="mt-3 text-xl font-medium">{paper.title}</h4>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {paper.authors.join(", ")} · {paper.venue}
              </p>
              <p className="mt-3 text-sm leading-6 text-foreground">{paper.summary}</p>
              <EvidenceLink className="mt-4" href={paper.sourceUrl}>
                Inspect fictional paper record
              </EvidenceLink>
            </article>
          ))}
        </div>
      </section>

      <DraftWorkspace mentor={mentor} />
    </article>
  );
}

function MentorWorkspace() {
  const { catalog, dispatch, state } = useReadyDemoStore();
  const selectedMentor = catalog.mentors.find(
    (mentor) => mentor.id === state.selectedMentorId,
  );

  function selectMentor(mentorId: string) {
    dispatch({ type: "select-mentor", mentorId });
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[21rem_minmax(0,1fr)] lg:items-start lg:gap-10">
      <div className={cn(selectedMentor && "hidden lg:block", "lg:sticky lg:top-24")}>
        <MentorList
          mentors={catalog.mentors}
          onSelect={selectMentor}
          selectedMentorId={state.selectedMentorId}
        />
      </div>

      <div className={cn(!selectedMentor && "hidden lg:block")}>
        {selectedMentor ? (
          <MentorDetail
            key={selectedMentor.id}
            mentor={selectedMentor}
            onBack={() => dispatch({ type: "select-mentor", mentorId: null })}
          />
        ) : (
          <DataState
            description="Choose a fictional researcher from the candidate list. On mobile, the list becomes a dedicated first screen so the evidence remains readable."
            kind="empty"
            title="Select a researcher to inspect the evidence"
          />
        )}
      </div>
    </div>
  );
}

export function MentorExperience() {
  return (
    <DemoDataBoundary
      loadingDescription="Loading fictional mentor and paper evidence from FastAPI, then restoring compatible selections."
      loadingTitle="Loading mentor evidence"
    >
      <MentorWorkspace />
    </DemoDataBoundary>
  );
}
