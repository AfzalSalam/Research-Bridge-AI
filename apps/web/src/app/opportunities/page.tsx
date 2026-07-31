import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { DemoNotice } from "@/features/demo/components/demo-notice";
import { WorkflowSteps } from "@/features/demo/components/workflow-steps";
import { OpportunitiesExperience } from "@/features/opportunities/opportunities-experience";

export const metadata: Metadata = {
  title: "Research Opportunities",
  description: "The future verified research opportunity workspace.",
};

export default function OpportunitiesPage() {
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Filter fictional opportunities, inspect their source metadata, and save only what you intend to review. Unknown fields remain explicit."
          eyebrow="Step 4 · Save"
          title="Research openings you can verify"
        />
        <WorkflowSteps current="Save" />
        <DemoNotice className="mt-8" />
        <div className="mt-8">
          <OpportunitiesExperience />
        </div>
      </Container>
    </main>
  );
}
