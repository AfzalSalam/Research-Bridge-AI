import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { DemoNotice } from "@/features/demo/components/demo-notice";
import { WorkflowSteps } from "@/features/demo/components/workflow-steps";
import { DiscoveryExperience } from "@/features/discovery/discovery-experience";

export const metadata: Metadata = {
  title: "Discover Research",
  description: "The future academic paper discovery workspace.",
};

export default function DiscoverPage() {
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Run a transparent local retrieval simulation, inspect partial failures, and move from a topic to fictional paper-backed researcher candidates."
          eyebrow="Step 2 · Discover"
          title="Start with the evidence"
        />
        <WorkflowSteps current="Discover" />
        <DemoNotice className="mt-8" />
        <div className="mt-8">
          <DiscoveryExperience />
        </div>
      </Container>
    </main>
  );
}
