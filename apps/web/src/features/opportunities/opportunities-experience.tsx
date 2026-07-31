"use client";

import { Bookmark, BookmarkCheck, CalendarDays, ClipboardPlus, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { DataState } from "@/components/states/data-state";
import { StatusBadge } from "@/components/status/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EvidenceLink } from "@/features/demo/components/evidence-link";
import { NativeSelect } from "@/features/demo/components/native-select";
import { applicationSchema } from "@/features/demo/contracts";
import { useDemoStore } from "@/features/demo/demo-store";
import { demoOpportunities } from "@/features/demo/fixtures";

type FixtureMode = "complete" | "partial" | "error";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
}

function OpportunitiesWorkspace() {
  const { dispatch, state } = useDemoStore();
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("All");
  const [fixtureMode, setFixtureMode] = useState<FixtureMode>("complete");
  const [loadedMode, setLoadedMode] = useState<FixtureMode>("complete");
  const [loading, setLoading] = useState(false);
  const [announcement, setAnnouncement] = useState("");

  useEffect(() => {
    if (!loading) return;
    const timer = window.setTimeout(() => {
      setLoadedMode(fixtureMode);
      setLoading(false);
    }, 450);
    return () => window.clearTimeout(timer);
  }, [fixtureMode, loading]);

  const availableFixtures =
    loadedMode === "partial" ? demoOpportunities.slice(0, 2) : demoOpportunities;

  const visibleOpportunities = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return availableFixtures.filter((opportunity) => {
      const matchesQuery =
        !normalizedQuery ||
        [
          opportunity.title,
          opportunity.organisation,
          opportunity.description,
          ...opportunity.topics,
        ]
          .join(" ")
          .toLowerCase()
          .includes(normalizedQuery);
      const matchesMode = mode === "All" || opportunity.mode === mode;
      return matchesQuery && matchesMode;
    });
  }, [availableFixtures, mode, query]);

  function saveOpportunity(opportunityId: string) {
    const isSaved = state.savedOpportunityIds.includes(opportunityId);
    dispatch({ type: "toggle-opportunity", opportunityId });
    setAnnouncement(isSaved ? "Opportunity removed from saved items." : "Opportunity saved in this browser session.");
  }

  function trackOpportunity(opportunityId: string) {
    const opportunity = demoOpportunities.find((item) => item.id === opportunityId);
    if (!opportunity) return;
    const changedAt = new Date().toISOString();
    dispatch({
      type: "track-application",
      application: applicationSchema.parse({
        id: `application-${opportunity.id}`,
        targetType: "opportunity",
        targetId: opportunity.id,
        targetLabel: opportunity.title,
        sourceUrl: opportunity.sourceUrl,
        status: "Saved",
        notes: "Fictional opportunity saved for source review.",
        followUpDate: null,
        updatedAt: changedAt,
        history: [{ status: "Saved", changedAt }],
      }),
    });
    setAnnouncement("Saved opportunity added to the application tracker.");
  }

  return (
    <div>
      <section className="border border-border bg-surface p-5 sm:p-7" aria-labelledby="filters-title">
        <div className="flex items-center gap-3">
          <Search aria-hidden="true" className="size-5 text-brand-teal" />
          <h2 className="text-xl font-medium" id="filters-title">Filter verified fields</h2>
        </div>
        <div className="mt-5 grid gap-5 md:grid-cols-[minmax(0,1fr)_12rem_14rem_auto] md:items-end">
          <div>
            <Label htmlFor="opportunity-query">Topic or organisation</Label>
            <Input
              className="mt-2"
              id="opportunity-query"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="e.g. mobile health"
              value={query}
            />
          </div>
          <div>
            <Label htmlFor="opportunity-mode">Work mode</Label>
            <NativeSelect className="mt-2" id="opportunity-mode" onChange={(event) => setMode(event.target.value)} value={mode}>
              <option>All</option>
              <option>On-site</option>
              <option>Hybrid</option>
              <option>Remote</option>
              <option>Unknown</option>
            </NativeSelect>
          </div>
          <div>
            <Label htmlFor="opportunity-fixture">Demo source response</Label>
            <NativeSelect
              className="mt-2"
              id="opportunity-fixture"
              onChange={(event) => setFixtureMode(event.target.value as FixtureMode)}
              value={fixtureMode}
            >
              <option value="complete">Complete fixtures</option>
              <option value="partial">Partial source</option>
              <option value="error">Source error</option>
            </NativeSelect>
          </div>
          <Button disabled={loading} onClick={() => setLoading(true)} variant="outline">
            Load scenario
          </Button>
        </div>
      </section>

      <p aria-live="polite" className="sr-only">{announcement}</p>

      <div className="mt-8">
        {loading ? (
          <DataState
            description="Loading local fictional opportunity records. No university site is being scraped in this phase."
            kind="loading"
            title="Checking the fixture source"
          />
        ) : null}

        {!loading && loadedMode === "error" ? (
          <DataState
            description="The selected fictional source failed. The interface does not substitute stale listings or guess whether applications are open."
            kind="error"
            title="Opportunity source unavailable"
          />
        ) : null}

        {!loading && loadedMode === "partial" ? (
          <DataState
            className="mb-6 min-h-0"
            description="Two fictional records were available; the third source did not respond. Existing records keep their own last-verified timestamps."
            kind="partial"
            title="One fixture source is missing"
          />
        ) : null}

        {!loading && loadedMode !== "error" && visibleOpportunities.length === 0 ? (
          <DataState
            action={<Button onClick={() => { setQuery(""); setMode("All"); }} variant="outline">Clear filters</Button>}
            description="No available fictional record matches these local filters. Unknown work modes are not treated as remote."
            kind="empty"
            title="No opportunities match the filters"
          />
        ) : null}

        {!loading && loadedMode !== "error" && visibleOpportunities.length > 0 ? (
          <section aria-labelledby="opportunities-title">
            <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-4">
              <div>
                <p className="text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">Fictional, source-linked records</p>
                <h2 className="mt-2 text-3xl font-medium" id="opportunities-title">Research opportunities</h2>
              </div>
              <StatusBadge tone="evidence">{visibleOpportunities.length} visible</StatusBadge>
            </div>

            <div className="grid gap-5 pt-6 lg:grid-cols-2">
              {visibleOpportunities.map((opportunity) => {
                const isSaved = state.savedOpportunityIds.includes(opportunity.id);
                const isTracked = state.applications.some(
                  (application) =>
                    application.targetType === "opportunity" &&
                    application.targetId === opportunity.id,
                );
                return (
                  <article className="flex flex-col border border-border bg-surface p-5 sm:p-6" key={opportunity.id}>
                    <div className="flex flex-wrap gap-2">
                      <StatusBadge tone={opportunity.availability === "Unknown" ? "unknown" : "evidence"}>
                        {opportunity.availability === "Unknown" ? "Availability unknown" : opportunity.availability}
                      </StatusBadge>
                      <StatusBadge tone={opportunity.funding === "Unknown" ? "unknown" : "neutral"}>
                        {opportunity.funding === "Unknown" ? "Funding unknown" : opportunity.funding}
                      </StatusBadge>
                      <StatusBadge tone={opportunity.mode === "Unknown" ? "unknown" : "neutral"}>
                        {opportunity.mode === "Unknown" ? "Mode unknown" : opportunity.mode}
                      </StatusBadge>
                    </div>
                    <h3 className="mt-5 text-2xl font-medium">{opportunity.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {opportunity.organisation} · {opportunity.location}
                    </p>
                    <p className="mt-4 text-sm leading-6 text-foreground">{opportunity.description}</p>
                    <ul className="mt-4 flex flex-wrap gap-2">
                      {opportunity.topics.map((topic) => (
                        <li className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground" key={topic}>{topic}</li>
                      ))}
                    </ul>
                    <div className="mt-5 border-t border-border pt-4 text-sm leading-6 text-muted-foreground">
                      <p className="flex items-center gap-2">
                        <CalendarDays aria-hidden="true" className="size-4 text-brand-indigo" />
                        Deadline: {opportunity.deadline ? formatDate(`${opportunity.deadline}T00:00:00.000Z`) : "Unknown"}
                      </p>
                      <p className="mt-1">Fixture last checked: {formatDate(opportunity.lastVerifiedAt)}</p>
                      <EvidenceLink className="mt-3" href={opportunity.sourceUrl}>Inspect fictional listing</EvidenceLink>
                    </div>
                    <div className="mt-auto flex flex-wrap gap-3 pt-6">
                      <Button onClick={() => saveOpportunity(opportunity.id)} variant={isSaved ? "evidence" : "outline"}>
                        {isSaved ? <BookmarkCheck aria-hidden="true" /> : <Bookmark aria-hidden="true" />}
                        {isSaved ? "Saved" : "Save opportunity"}
                      </Button>
                      <Button disabled={!isSaved || isTracked} onClick={() => trackOpportunity(opportunity.id)} variant="outline">
                        <ClipboardPlus aria-hidden="true" />
                        {isTracked ? "Tracked" : "Track"}
                      </Button>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}

export function OpportunitiesExperience() {
  const { hydrated } = useDemoStore();

  if (!hydrated) {
    return (
      <DataState
        description="Restoring saved fictional opportunities from this browser session."
        kind="loading"
        title="Loading opportunity fixtures"
      />
    );
  }

  return <OpportunitiesWorkspace />;
}
