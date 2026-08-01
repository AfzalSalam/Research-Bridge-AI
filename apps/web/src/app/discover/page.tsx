import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { WorkflowSteps } from "@/features/demo/components/workflow-steps";
import { DiscoveryExperience } from "@/features/discovery/discovery-experience";

export const metadata: Metadata = {
  title: "Discover Research",
  description: "Retrieve real OpenAlex papers with normalized evidence and provenance.",
};

export default function DiscoverPage() {
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Retrieve real OpenAlex publication evidence or switch to the deterministic recruiter journey. Every result keeps its source, uncertainty, and provider boundary visible."
          eyebrow="Step 2 · Discover"
          title="Start with the evidence"
        />
        <WorkflowSteps current="Discover" />
        <div className="mt-8">
          <DiscoveryExperience />
        </div>
      </Container>
    </main>
  );
}
