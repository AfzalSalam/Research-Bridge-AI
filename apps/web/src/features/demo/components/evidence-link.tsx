import { ExternalLink } from "lucide-react";

import { cn } from "@/lib/utils";

export function EvidenceLink({
  children = "Inspect source",
  className,
  href,
}: {
  children?: React.ReactNode;
  className?: string;
  href: string;
}) {
  return (
    <a
      className={cn(
        "inline-flex items-center gap-1.5 text-sm font-semibold text-brand-teal-strong underline decoration-brand-teal/35 underline-offset-4 hover:decoration-brand-teal",
        className,
      )}
      href={href}
      rel="noreferrer"
      target="_blank"
    >
      {children}
      <ExternalLink aria-hidden="true" className="size-3.5" />
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}
