import { ArrowRight, BookCheck, FileSearch, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { Container } from "@/components/layout/container";
import { HealthCard } from "@/components/health-card";
import { Button } from "@/components/ui/button";
import { getApiHealth } from "@/lib/api/health";

export const dynamic = "force-dynamic";

export default async function Home() {
  const health = await getApiHealth();

  return (
    <main id="main-content">
      <section className="border-b border-border">
        <Container className="grid min-h-[calc(100svh-4.5rem)] items-center gap-14 py-16 lg:grid-cols-[minmax(0,1.35fr)_minmax(21rem,0.65fr)] lg:gap-20 lg:py-24">
          <div className="max-w-4xl">
            <p className="text-xs font-bold tracking-[0.2em] text-brand-teal uppercase">
              Evidence-first academic discovery
            </p>
            <h1 className="mt-6 max-w-[16ch] text-[clamp(3.25rem,6vw,6.5rem)] leading-[0.94] font-normal tracking-[-0.05em]">
              Find the paper trail behind your next research mentor.
            </h1>
            <p className="mt-8 max-w-2xl text-lg leading-8 text-muted-foreground sm:text-xl sm:leading-9">
              Research Bridge AI turns a broad interest into reviewable papers,
              plausible mentors, visible evidence, and outreach you approve.
              Unknown facts remain unknown.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Button asChild size="lg" variant="evidence">
                <Link href="/discover">
                  Explore the shell
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/design-system">View design system</Link>
              </Button>
            </div>
          </div>

          <aside className="lg:pt-28" aria-label="Live system status">
            <p className="mb-3 text-xs font-bold tracking-[0.12em] text-brand-indigo uppercase">
              Phase 2 · Interface foundation
            </p>
            <HealthCard result={health} />
          </aside>
        </Container>
      </section>

      <section aria-labelledby="principles-title">
        <Container className="py-[var(--section-space)]">
          <div className="max-w-2xl">
            <p className="text-xs font-bold tracking-[0.18em] text-brand-teal uppercase">
              Product discipline
            </p>
            <h2
              className="mt-4 text-3xl font-medium tracking-[-0.025em] sm:text-4xl"
              id="principles-title"
            >
              Designed to make evidence easier to inspect—not easier to hide.
            </h2>
          </div>

          <div className="mt-12 grid border-y border-border md:grid-cols-3 md:divide-x md:divide-border">
            {[
              {
                title: "Paper-led discovery",
                description:
                  "Recommendations must retain the publications and source links that support them.",
                icon: FileSearch,
              },
              {
                title: "Unknown stays unknown",
                description:
                  "Availability, funding, contact details, and work mode are never guessed for polish.",
                icon: ShieldCheck,
              },
              {
                title: "Human-approved outreach",
                description:
                  "The student selects the mentor and paper evidence, then reviews every editable draft.",
                icon: BookCheck,
              },
            ].map(({ description, icon: Icon, title }) => (
              <article
                className="border-b border-border py-8 last:border-b-0 md:border-b-0 md:px-8 md:first:pl-0 md:last:pr-0"
                key={title}
              >
                <Icon
                  aria-hidden="true"
                  className="size-6 text-brand-indigo"
                  strokeWidth={1.7}
                />
                <h3 className="mt-6 text-2xl font-medium">{title}</h3>
                <p className="mt-3 leading-7 text-muted-foreground">
                  {description}
                </p>
              </article>
            ))}
          </div>
        </Container>
      </section>
    </main>
  );
}
