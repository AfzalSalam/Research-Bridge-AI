import type { ReactNode } from "react";

export function FactRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="grid gap-1 border-b border-border py-3 last:border-b-0 sm:grid-cols-[9rem_minmax(0,1fr)] sm:gap-4">
      <dt className="text-xs font-bold tracking-[0.08em] text-muted-foreground uppercase">
        {label}
      </dt>
      <dd className="text-sm leading-6 text-foreground">{value}</dd>
    </div>
  );
}
