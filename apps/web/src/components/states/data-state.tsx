import type { ReactNode } from "react";
import {
  CircleAlert,
  CloudOff,
  FileQuestion,
  LoaderCircle,
  TriangleAlert,
} from "lucide-react";

import { StatusBadge } from "@/components/status/status-badge";
import { cn } from "@/lib/utils";

export type DataStateKind =
  | "empty"
  | "error"
  | "loading"
  | "partial"
  | "unavailable";

interface DataStateProps {
  action?: ReactNode;
  className?: string;
  description: string;
  kind: DataStateKind;
  title: string;
}

const stateConfig = {
  loading: {
    icon: LoaderCircle,
    label: "Loading",
    tone: "neutral",
  },
  empty: {
    icon: FileQuestion,
    label: "No results yet",
    tone: "neutral",
  },
  error: {
    icon: CircleAlert,
    label: "Action needed",
    tone: "error",
  },
  partial: {
    icon: TriangleAlert,
    label: "Partial result",
    tone: "unknown",
  },
  unavailable: {
    icon: CloudOff,
    label: "Unavailable",
    tone: "unknown",
  },
} as const;

export function DataState({
  action,
  className,
  description,
  kind,
  title,
}: DataStateProps) {
  const config = stateConfig[kind];
  const Icon = config.icon;
  const isLoading = kind === "loading";

  return (
    <section
      aria-busy={isLoading || undefined}
      aria-label={title}
      className={cn(
        "grid min-h-64 content-center justify-items-start border border-border bg-surface p-6 sm:p-8",
        className,
      )}
      role={kind === "error" ? "alert" : isLoading ? "status" : undefined}
    >
      <div className="grid size-11 place-items-center rounded-full bg-muted text-muted-foreground">
        <Icon
          aria-hidden="true"
          className={cn("size-5", isLoading && "animate-spin motion-reduce:animate-none")}
          strokeWidth={1.8}
        />
      </div>
      <div className="mt-5">
        <StatusBadge tone={config.tone}>{config.label}</StatusBadge>
      </div>
      <h2 className="mt-4 text-2xl font-medium tracking-[-0.02em]">{title}</h2>
      <p className="mt-2 max-w-xl leading-7 text-muted-foreground">
        {description}
      </p>
      {action ? <div className="mt-6">{action}</div> : null}
    </section>
  );
}
