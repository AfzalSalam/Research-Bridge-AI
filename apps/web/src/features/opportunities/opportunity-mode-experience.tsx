"use client";

import { type KeyboardEvent, useRef, useState } from "react";

import { DemoNotice } from "@/features/demo/components/demo-notice";
import { LiveOpportunities } from "@/features/opportunities/live-opportunities";
import { OpportunitiesExperience } from "@/features/opportunities/opportunities-experience";

export function OpportunityModeExperience() {
  const [mode, setMode] = useState<"live" | "demo">("live");
  const liveRef = useRef<HTMLButtonElement>(null);
  const demoRef = useRef<HTMLButtonElement>(null);

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const nextMode =
      event.key === "ArrowLeft" || event.key === "Home"
        ? "live"
        : event.key === "ArrowRight" || event.key === "End"
          ? "demo"
          : null;
    if (nextMode === null) return;
    event.preventDefault();
    setMode(nextMode);
    (nextMode === "live" ? liveRef : demoRef).current?.focus();
  }

  return (
    <div>
      <div
        aria-label="Opportunity data mode"
        className="mb-8 grid gap-1 border border-border bg-surface-subtle p-1 sm:inline-grid sm:grid-cols-2"
        role="tablist"
      >
        <button
          aria-controls="live-opportunities-panel"
          aria-selected={mode === "live"}
          className="min-h-11 px-5 text-sm font-semibold transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring aria-selected:bg-surface aria-selected:text-brand-teal-strong aria-selected:shadow-xs"
          id="live-opportunities-tab"
          onClick={() => setMode("live")}
          onKeyDown={handleTabKeyDown}
          ref={liveRef}
          role="tab"
          tabIndex={mode === "live" ? 0 : -1}
          type="button"
        >
          Live verified opportunities
        </button>
        <button
          aria-controls="demo-opportunities-panel"
          aria-selected={mode === "demo"}
          className="min-h-11 px-5 text-sm font-semibold transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring aria-selected:bg-surface aria-selected:text-brand-indigo aria-selected:shadow-xs"
          id="demo-opportunities-tab"
          onClick={() => setMode("demo")}
          onKeyDown={handleTabKeyDown}
          ref={demoRef}
          role="tab"
          tabIndex={mode === "demo" ? 0 : -1}
          type="button"
        >
          Recruiter demo fixtures
        </button>
      </div>
      {mode === "live" ? (
        <div
          aria-labelledby="live-opportunities-tab"
          id="live-opportunities-panel"
          role="tabpanel"
        >
          <LiveOpportunities />
        </div>
      ) : (
        <div
          aria-labelledby="demo-opportunities-tab"
          id="demo-opportunities-panel"
          role="tabpanel"
        >
          <DemoNotice className="mb-8" />
          <OpportunitiesExperience />
        </div>
      )}
    </div>
  );
}
