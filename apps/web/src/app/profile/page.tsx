import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { DemoNotice } from "@/features/demo/components/demo-notice";
import { WorkflowSteps } from "@/features/demo/components/workflow-steps";
import { ProfileExperience } from "@/features/profile/profile-experience";

export const metadata: Metadata = {
  title: "Research Profile",
  description: "The evidence boundary for research matching and grounded outreach.",
};

export default function ProfilePage() {
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Edit a fictional student profile and establish exactly which facts later explanations and drafts may reuse."
          eyebrow="Step 1 · Profile"
          title="Your research profile, grounded in facts"
        />
        <WorkflowSteps current="Profile" />
        <DemoNotice className="mt-8" />
        <div className="mt-8">
          <ProfileExperience />
        </div>
      </Container>
    </main>
  );
}
