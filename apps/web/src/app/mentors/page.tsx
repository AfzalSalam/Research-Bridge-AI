import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { DemoNotice } from "@/features/demo/components/demo-notice";
import { WorkflowSteps } from "@/features/demo/components/workflow-steps";
import { MentorExperience } from "@/features/mentors/mentor-experience";

export const metadata: Metadata = {
  title: "Research Mentors",
  description: "The future professor evidence and matching workspace.",
};

export default function MentorsPage() {
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Inspect exactly why a fictional researcher appears, choose specific papers, and create a cautious outreach draft that remains yours to edit."
          eyebrow="Step 3 · Evidence"
          title="Understand the researcher before the match"
        />
        <WorkflowSteps current="Evidence" />
        <DemoNotice className="mt-8" />
        <div className="mt-8">
          <MentorExperience />
        </div>
      </Container>
    </main>
  );
}
