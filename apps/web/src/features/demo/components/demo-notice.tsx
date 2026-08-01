"use client";

import { FlaskConical, RotateCcw } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useDemoStore } from "@/features/demo/demo-store";
import { cn } from "@/lib/utils";

export function DemoNotice({ className }: { className?: string }) {
  const {
    bootstrapStatus,
    resetDemo: resetDemoState,
    storageWarning,
  } = useDemoStore();
  const [announcement, setAnnouncement] = useState("");

  function resetDemo() {
    resetDemoState();
    setAnnouncement("The fictional demo has been restored to its starting state.");
  }

  return (
    <aside
      className={cn(
        "flex flex-col gap-4 border border-brand-indigo/20 bg-brand-indigo-soft/60 p-5 sm:flex-row sm:items-center sm:justify-between",
        className,
      )}
    >
      <div className="flex min-w-0 gap-3">
        <FlaskConical
          aria-hidden="true"
          className="mt-0.5 size-5 shrink-0 text-brand-indigo"
          strokeWidth={1.8}
        />
        <div>
          <p className="text-sm font-bold text-foreground">Fictional recruiter demo</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Every person, paper, institution, and opportunity is invented. Changes stay
            only in this browser session; do not enter private or real personal data.
          </p>
          {storageWarning ? (
            <p className="mt-2 text-sm font-semibold leading-6 text-warning-foreground">
              {storageWarning}
            </p>
          ) : null}
        </div>
      </div>
      <Button
        className="shrink-0"
        disabled={bootstrapStatus !== "ready"}
        onClick={resetDemo}
        size="sm"
        variant="outline"
      >
        <RotateCcw aria-hidden="true" />
        Reset demo
      </Button>
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>
    </aside>
  );
}
