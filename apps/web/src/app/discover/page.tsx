import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { DiscoveryExperience } from "@/features/discovery/discovery-experience";
import { WorkflowPanel } from "@/features/workflow/workflow-panel";

export const metadata: Metadata = {
  title: "Discover Research",
  description:
    "Search real academic papers and discover professors whose published work aligns with your research interests.",
};

export default function DiscoverPage() {
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Enter a research topic to find real academic papers from OpenAlex, ranked professors backed by their publications, and generate a grounded outreach draft — all in one guided workflow."
          eyebrow="Step 1 · Discover"
          title="Start with the evidence"
        />
        <div className="mt-10 flex flex-col gap-12 lg:gap-16">
          <section aria-labelledby="guided-workflow-heading">
            <h2
              id="guided-workflow-heading"
              className="mb-2 text-xl font-semibold tracking-tight"
            >
              Guided discovery journey
            </h2>
            <p className="mb-6 text-sm text-muted-foreground max-w-2xl">
              Enter a research interest to discover ranked mentors backed by
              real papers, select your evidence, and generate a grounded
              outreach draft.
            </p>
            <WorkflowPanel />
          </section>

          <section aria-labelledby="paper-search-heading" className="border-t border-border pt-12">
            <h2
              id="paper-search-heading"
              className="mb-2 text-xl font-semibold tracking-tight"
            >
              Search papers directly
            </h2>
            <p className="mb-6 text-sm text-muted-foreground max-w-2xl">
              Browse raw OpenAlex results to explore a topic before starting a
              full discovery workflow.
            </p>
            <DiscoveryExperience />
          </section>
        </div>
      </Container>
    </main>
  );
}
