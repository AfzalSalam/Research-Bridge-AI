import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { WorkflowSteps } from "@/features/demo/components/workflow-steps";
import { OpportunityModeExperience } from "@/features/opportunities/opportunity-mode-experience";

export const metadata: Metadata = {
  title: "Research Opportunities",
  description: "Verified, source-linked research opportunities with explicit unknowns.",
};

export default function OpportunitiesPage() {
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Search employer-published research openings, inspect exactly what was verified, and move only deliberate choices into your tracker."
          eyebrow="Step 4 · Save"
          title="Research openings you can verify"
        />
        <WorkflowSteps current="Save" />
        <div className="mt-8">
          <OpportunityModeExperience />
        </div>
      </Container>
    </main>
  );
}
