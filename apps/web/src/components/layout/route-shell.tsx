import { ArrowLeft, Layers3 } from "lucide-react";
import Link from "next/link";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { DataState } from "@/components/states/data-state";
import { Button } from "@/components/ui/button";

interface RouteShellProps {
  description: string;
  eyebrow: string;
  plannedItems: readonly string[];
  stateDescription: string;
  stateTitle: string;
  title: string;
}

export function RouteShell({
  description,
  eyebrow,
  plannedItems,
  stateDescription,
  stateTitle,
  title,
}: RouteShellProps) {
  return (
    <main id="main-content">
      <Container className="py-12 sm:py-16 lg:py-20">
        <PageHeader
          actions={
            <Button asChild variant="outline">
              <Link href="/">
                <ArrowLeft aria-hidden="true" />
                Back to overview
              </Link>
            </Button>
          }
          description={description}
          eyebrow={eyebrow}
          title={title}
        />

        <div className="grid gap-8 pt-10 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
          <DataState
            description={stateDescription}
            kind="empty"
            title={stateTitle}
          />

          <aside className="border border-border bg-surface p-6" aria-labelledby={`${eyebrow}-scope`}>
            <div className="grid size-10 place-items-center rounded-full bg-brand-indigo-soft text-brand-indigo">
              <Layers3 aria-hidden="true" className="size-5" strokeWidth={1.8} />
            </div>
            <h2
              className="mt-5 text-xl font-medium tracking-[-0.02em]"
              id={`${eyebrow}-scope`}
            >
              Planned product surface
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              This phase establishes the interface boundary only. The following
              capabilities arrive in their approved implementation phases.
            </p>
            <ul className="mt-5 space-y-3 border-t border-border pt-5">
              {plannedItems.map((item) => (
                <li
                  className="grid grid-cols-[0.45rem_minmax(0,1fr)] gap-3 text-sm leading-6 text-foreground"
                  key={item}
                >
                  <span
                    aria-hidden="true"
                    className="mt-[0.55rem] size-1.5 rounded-full bg-brand-teal"
                  />
                  {item}
                </li>
              ))}
            </ul>
          </aside>
        </div>
      </Container>
    </main>
  );
}
