"use client";

import { type KeyboardEvent, useRef, useState } from "react";

import { ApplicationsExperience } from "@/features/applications/applications-experience";
import { LiveApplications } from "@/features/applications/live-applications";
import { DemoNotice } from "@/features/demo/components/demo-notice";

export function ApplicationModeExperience() {
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
        aria-label="Application tracker mode"
        className="mb-8 grid gap-1 border border-border bg-surface-subtle p-1 sm:inline-grid sm:grid-cols-2"
        role="tablist"
      >
        <button
          aria-controls="live-applications-panel"
          aria-selected={mode === "live"}
          className="min-h-11 px-5 text-sm font-semibold transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring aria-selected:bg-surface aria-selected:text-brand-teal-strong aria-selected:shadow-xs"
          id="live-applications-tab"
          onClick={() => setMode("live")}
          onKeyDown={handleTabKeyDown}
          ref={liveRef}
          role="tab"
          tabIndex={mode === "live" ? 0 : -1}
          type="button"
        >
          Live durable tracker
        </button>
        <button
          aria-controls="demo-applications-panel"
          aria-selected={mode === "demo"}
          className="min-h-11 px-5 text-sm font-semibold transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring aria-selected:bg-surface aria-selected:text-brand-indigo aria-selected:shadow-xs"
          id="demo-applications-tab"
          onClick={() => setMode("demo")}
          onKeyDown={handleTabKeyDown}
          ref={demoRef}
          role="tab"
          tabIndex={mode === "demo" ? 0 : -1}
          type="button"
        >
          Recruiter demo tracker
        </button>
      </div>
      {mode === "live" ? (
        <div aria-labelledby="live-applications-tab" id="live-applications-panel" role="tabpanel">
          <LiveApplications />
        </div>
      ) : (
        <div aria-labelledby="demo-applications-tab" id="demo-applications-panel" role="tabpanel">
          <DemoNotice className="mb-8" />
          <ApplicationsExperience />
        </div>
      )}
    </div>
  );
}
