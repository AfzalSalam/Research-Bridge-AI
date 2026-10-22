"use client";

/**
 * WorkflowPanel — the main UI for the two-phase placement journey.
 *
 * Phase 1: Enter a query → stream discover_mentors → see ranked candidates.
 * Phase 2: Select a mentor + 1-2 papers → stream generate_draft → review draft.
 *
 * No auto-send. Human approves every step.
 */

import { z } from "zod";
import { useResearchValue } from "@/features/discovery/research-session";
import { useWorkflow } from "@/features/workflow/use-workflow";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, RefreshCw, ChevronRight, Mail } from "lucide-react";

export function WorkflowPanel() {
  const { state, start, resume, reset } = useWorkflow();
  const [query, setQuery] = useResearchValue("workflow-query", z.string(), "");
  const [selectedMentorId, setSelectedMentorId] = useResearchValue("workflow-mentor", z.string().nullable(), null);
  const [selectedPaperIds, setSelectedPaperIds] = useResearchValue("workflow-papers", z.array(z.string()), []);

  // Phase 1 submit
  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    start(query.trim());
  }

  // Phase 2 submit
  function handleDraft(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedMentorId || selectedPaperIds.length === 0) return;
    resume(selectedMentorId, selectedPaperIds);
  }

  function togglePaper(id: string) {
    setSelectedPaperIds((prev) =>
      prev.includes(id)
        ? prev.filter((p) => p !== id)
        : prev.length < 2
          ? [...prev, id]
          : prev
    );
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  const candidates = state.discoveryResponse?.candidates ?? [];
  const selectedMentor = candidates.find((c) => c.id === selectedMentorId);
  const draft = state.draftResponse;

  return (
    <div className="space-y-6">
      {/* ── Query bar ─────────────────────────────────────────────────── */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <Input
          aria-label="Guided research topic"
          placeholder="e.g. transformer efficiency in edge devices"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={state.phase !== "idle" && state.phase !== "error"}
          className="flex-1"
        />
        <Button
          type="submit"
          disabled={
            !query.trim() ||
            state.phase === "discovering" ||
            state.phase === "generating"
          }
        >
          {state.phase === "discovering" ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <ChevronRight className="mr-2 h-4 w-4" />
          )}
          Find Mentors
        </Button>
        {state.phase !== "idle" && (
          <Button
            type="button"
            aria-label="Reset guided journey"
            variant="outline"
            onClick={() => {
              reset();
              setQuery("");
              setSelectedMentorId(null);
              setSelectedPaperIds([]);
            }}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        )}
      </form>

      {/* ── Discovering spinner ───────────────────────────────────────── */}
      {state.phase === "discovering" && (
        <div className="flex items-center gap-3 rounded-lg border bg-muted/40 p-4">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">
            Searching papers and ranking mentors…
          </span>
        </div>
      )}

      {/* ── Discovery error ───────────────────────────────────────────── */}
      {state.discoveryError && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          Discovery error: {state.discoveryError}
        </div>
      )}

      {/* ── Candidate list (Phase 1 done) ─────────────────────────────── */}
      {state.phase === "awaiting_selection" && candidates.length === 0 && (
        <p role="status" className="text-sm text-muted-foreground">No mentor evidence was found. Reset the journey and try a broader topic.</p>
      )}
      {state.discoveryResponse?.status === "partial" && (
        <p role="status" className="text-sm text-muted-foreground">Some source records were unavailable. {state.discoveryResponse.warnings.join(" ")}</p>
      )}
      {(state.phase === "awaiting_selection" ||
        state.phase === "generating" ||
        state.phase === "done") &&
        candidates.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm font-medium text-muted-foreground">
              {candidates.length} mentor candidates — select one to draft an email
            </p>
            <div className="divide-y rounded-lg border">
              {candidates.slice(0, 8).map((c) => {
                const isSelected = c.id === selectedMentorId;
                return (
                  <button
                    key={c.id}
                    onClick={() => {
                      if (state.phase !== "awaiting_selection") return;
                      setSelectedMentorId(isSelected ? null : c.id);
                      setSelectedPaperIds([]);
                    }}
                    disabled={state.phase !== "awaiting_selection"}
                    className={`flex w-full items-start gap-3 p-3 text-left transition-colors hover:bg-muted/40 ${
                      isSelected ? "bg-primary/5 ring-1 ring-primary/30" : ""
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">
                        {c.displayName}
                      </p>
                      <span
                        className={`mt-1 inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${
                          c.relevanceBand === "strong"
                            ? "bg-brand-teal-soft text-brand-teal-strong"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {c.relevanceBand}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

      {/* ── Paper selection for selected mentor ───────────────────────── */}
      {state.phase === "awaiting_selection" && selectedMentor && (
        <form onSubmit={handleDraft} className="space-y-3">
          <p className="text-sm font-medium text-muted-foreground">
            Select 1–2 supporting papers (your evidence for the email)
          </p>
          <div className="space-y-2">
            {selectedMentor.supportingPapers.slice(0, 5).map((p) => {
              const checked = selectedPaperIds.includes(p.id);
              return (
                <label
                  key={p.id}
                  className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/40 ${
                    checked ? "bg-primary/5 ring-1 ring-primary/30" : ""
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => togglePaper(p.id)}
                    className="mt-0.5"
                  />
                  <div>
                    <p className="text-sm font-medium leading-snug">{p.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {p.publicationYear}
                    </p>
                  </div>
                </label>
              );
            })}
          </div>
          <Button
            type="submit"
            disabled={selectedPaperIds.length === 0}
            className="w-full"
          >
            <Mail className="mr-2 h-4 w-4" />
            Generate Outreach Draft
          </Button>
        </form>
      )}

      {/* ── Generating spinner ────────────────────────────────────────── */}
      {state.phase === "generating" && (
        <div className="flex items-center gap-3 rounded-lg border bg-muted/40 p-4">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">
            Drafting evidence-grounded email…
          </span>
        </div>
      )}

      {/* ── Draft error ───────────────────────────────────────────────── */}
      {state.draftError && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          Draft error: {state.draftError}
        </div>
      )}

      {/* ── Completed draft ───────────────────────────────────────────── */}
      {state.phase === "done" && draft && (
        <div className="space-y-3 rounded-lg border bg-card p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Draft ready — review before sending
          </p>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Subject</p>
            <p className="font-medium text-sm">{draft.subject}</p>
          </div>
          <hr />
          <pre className="whitespace-pre-wrap text-sm font-sans leading-relaxed">
            {draft.body}
          </pre>
          <p className="text-xs text-muted-foreground">
            Review the wording against your selected evidence before using this draft.
          </p>
        </div>
      )}

      {/* ── Top-level error ───────────────────────────────────────────── */}
      {state.phase === "error" && state.errorMessage && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          {state.errorMessage}
        </div>
      )}
    </div>
  );
}
