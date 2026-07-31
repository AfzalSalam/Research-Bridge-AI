import { Check, Circle, LoaderCircle } from "lucide-react";

import { cn } from "@/lib/utils";

const stages = [
  {
    title: "Validate request",
    description: "Check the topic and selected fixture scenario.",
  },
  {
    title: "Load paper fixtures",
    description: "Read local fictional records; no academic API is called.",
  },
  {
    title: "Connect authors to evidence",
    description: "Retain source links and surface incomplete metadata.",
  },
  {
    title: "Prepare review set",
    description: "Present demo order without scores or ranking claims.",
  },
] as const;

export function ProgressStages({ activeStage }: { activeStage: number }) {
  return (
    <ol aria-label="Simulated discovery progress" className="grid gap-3 sm:grid-cols-2">
      {stages.map((stage, index) => {
        const isComplete = index < activeStage;
        const isActive = index === activeStage;
        const Icon = isComplete ? Check : isActive ? LoaderCircle : Circle;

        return (
          <li
            className={cn(
              "grid grid-cols-[2.25rem_minmax(0,1fr)] gap-3 border p-4",
              isActive ? "border-brand-teal/40 bg-brand-teal-soft/55" : "border-border bg-surface",
            )}
            key={stage.title}
          >
            <span
              className={cn(
                "grid size-8 place-items-center rounded-full",
                isComplete || isActive
                  ? "bg-brand-teal text-white"
                  : "bg-muted text-muted-foreground",
              )}
            >
              <Icon
                aria-hidden="true"
                className={cn("size-4", isActive && "animate-spin motion-reduce:animate-none")}
              />
            </span>
            <div>
              <p className="text-sm font-bold text-foreground">{stage.title}</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                {stage.description}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
