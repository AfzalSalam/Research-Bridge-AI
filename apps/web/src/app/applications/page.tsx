import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { ApplicationModeExperience } from "@/features/applications/application-mode-experience";
import { WorkflowSteps } from "@/features/demo/components/workflow-steps";

export const metadata: Metadata = {
  title: "Application Tracker",
  description: "A durable, explicit research application status history.",
};

export default function ApplicationsPage() {
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Keep notes, follow-up dates, and explicit status history without confusing preparation inside this app with submission elsewhere."
          eyebrow="Step 5 · Track"
          title="Keep every research conversation accountable"
        />
        <WorkflowSteps current="Track" />
        <div className="mt-8">
          <ApplicationModeExperience />
        </div>
      </Container>
    </main>
  );
}
