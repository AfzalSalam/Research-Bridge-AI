import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { ApplicationsExperience } from "@/features/applications/applications-experience";
import { DemoNotice } from "@/features/demo/components/demo-notice";
import { WorkflowSteps } from "@/features/demo/components/workflow-steps";

export const metadata: Metadata = {
  title: "Application Tracker",
  description: "The future research application tracking workspace.",
};

export default function ApplicationsPage() {
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Move saved opportunities and human-reviewed outreach through explicit states without confusing preparation with submission."
          eyebrow="Step 5 · Track"
          title="Keep every research conversation accountable"
        />
        <WorkflowSteps current="Track" />
        <DemoNotice className="mt-8" />
        <div className="mt-8">
          <ApplicationsExperience />
        </div>
      </Container>
    </main>
  );
}
