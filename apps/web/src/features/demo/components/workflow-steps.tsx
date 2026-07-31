"use client";

import { Check } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

const steps = [
  { href: "/profile", label: "Profile" },
  { href: "/discover", label: "Discover" },
  { href: "/mentors", label: "Evidence" },
  { href: "/opportunities", label: "Save" },
  { href: "/applications", label: "Track" },
] as const;

export function WorkflowSteps({ current }: { current: (typeof steps)[number]["label"] }) {
  const currentIndex = steps.findIndex((step) => step.label === current);
  const currentStepRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    currentStepRef.current?.scrollIntoView({
      behavior: "auto",
      block: "nearest",
      inline: "center",
    });
  }, [current]);

  return (
    <nav aria-label="Demo workflow" className="overflow-x-auto border-y border-border py-4">
      <ol className="flex min-w-max items-center gap-2">
        {steps.map((step, index) => {
          const isCurrent = step.label === current;
          const isComplete = index < currentIndex;

          return (
            <li className="flex items-center gap-2" key={step.href}>
              <Link
                aria-current={isCurrent ? "step" : undefined}
                className={cn(
                  "inline-flex min-h-9 items-center gap-2 rounded-full border px-3 text-xs font-bold tracking-[0.04em] uppercase transition-colors motion-reduce:transition-none",
                  isCurrent && "border-brand-teal bg-brand-teal text-white",
                  isComplete && "border-brand-teal/20 bg-brand-teal-soft text-brand-teal-strong",
                  !isCurrent && !isComplete && "border-border bg-surface text-muted-foreground hover:text-foreground",
                )}
                href={step.href}
                ref={isCurrent ? currentStepRef : undefined}
              >
                <span
                  className={cn(
                    "grid size-5 place-items-center rounded-full border text-[0.65rem]",
                    isCurrent ? "border-white/50" : "border-current/25",
                  )}
                >
                  {isComplete ? <Check aria-hidden="true" className="size-3" /> : index + 1}
                </span>
                {step.label}
              </Link>
              {index < steps.length - 1 ? (
                <span aria-hidden="true" className="h-px w-5 bg-border" />
              ) : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
