import type { HealthResult } from "@/lib/api/health";

import { StatusBadge } from "@/components/status/status-badge";

interface HealthCardProps {
  result: HealthResult;
}

export function HealthCard({ result }: HealthCardProps) {
  const isAvailable = result.state === "available";

  return (
    <section
      className="border border-border bg-surface p-6 sm:p-7"
      aria-labelledby="system-status-title"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[0.6875rem] font-bold tracking-[0.16em] text-brand-teal uppercase">
            Live foundation signal
          </p>
          <h2
            className="mt-2 text-2xl font-medium tracking-[-0.02em]"
            id="system-status-title"
          >
            Frontend to API
          </h2>
        </div>
        <div role="status">
          <StatusBadge tone={isAvailable ? "evidence" : "unknown"}>
            {isAvailable ? "API available" : "API unavailable"}
          </StatusBadge>
        </div>
      </div>

      {isAvailable ? (
        <dl className="mt-7 divide-y divide-border border-y border-border">
          <div className="grid grid-cols-[7rem_minmax(0,1fr)] gap-4 py-3.5">
            <dt className="text-xs font-bold tracking-[0.08em] text-muted-foreground uppercase">
              Service
            </dt>
            <dd className="m-0 [overflow-wrap:anywhere]">
              {result.data.service}
            </dd>
          </div>
          <div className="grid grid-cols-[7rem_minmax(0,1fr)] gap-4 py-3.5">
            <dt className="text-xs font-bold tracking-[0.08em] text-muted-foreground uppercase">
              Version
            </dt>
            <dd className="m-0">{result.data.version}</dd>
          </div>
          <div className="grid grid-cols-[7rem_minmax(0,1fr)] gap-4 py-3.5">
            <dt className="text-xs font-bold tracking-[0.08em] text-muted-foreground uppercase">
              Environment
            </dt>
            <dd className="m-0 [overflow-wrap:anywhere]">
              {result.data.environment}
            </dd>
          </div>
        </dl>
      ) : (
        <p className="mt-7 border-t border-border pt-5 leading-7 text-muted-foreground">
          {result.message}
        </p>
      )}
    </section>
  );
}
