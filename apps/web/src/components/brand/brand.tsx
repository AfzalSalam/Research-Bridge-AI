import { BookOpen } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";

interface BrandProps {
  className?: string;
  compact?: boolean;
}

export function Brand({ className, compact = false }: BrandProps) {
  return (
    <Link
      aria-label="Research Bridge AI home"
      className={cn(
        "group inline-flex min-h-11 items-center gap-3 rounded-sm font-serif text-lg font-semibold tracking-[-0.015em] text-foreground no-underline",
        className,
      )}
      href="/"
    >
      <span className="grid size-10 place-items-center rounded-sm bg-brand-indigo text-white transition-colors group-hover:bg-brand-teal motion-reduce:transition-none">
        <BookOpen aria-hidden="true" className="size-5" strokeWidth={1.8} />
      </span>
      <span className={cn(compact && "sr-only")}>Research Bridge AI</span>
    </Link>
  );
}
