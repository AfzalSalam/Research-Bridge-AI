import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type StatusTone = "error" | "evidence" | "neutral" | "unknown";

interface StatusBadgeProps {
  children: ReactNode;
  tone?: StatusTone;
}

const toneStyles: Record<StatusTone, string> = {
  evidence: "bg-brand-teal",
  unknown: "bg-warning",
  error: "bg-destructive",
  neutral: "bg-muted-foreground",
};

const toneVariants: Record<
  StatusTone,
  "destructive" | "evidence" | "outline" | "unknown"
> = {
  evidence: "evidence",
  unknown: "unknown",
  error: "destructive",
  neutral: "outline",
};

export function StatusBadge({
  children,
  tone = "neutral",
}: StatusBadgeProps) {
  return (
    <Badge variant={toneVariants[tone]}>
      <span
        aria-hidden="true"
        className={cn("size-1.5 rounded-full", toneStyles[tone])}
      />
      {children}
    </Badge>
  );
}
