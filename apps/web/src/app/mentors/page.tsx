import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { WorkflowSteps } from "@/features/demo/components/workflow-steps";
import { MentorModeExperience } from "@/features/mentors/mentor-mode-experience";

export const metadata: Metadata = {
  title: "Research Mentors",
  description: "Explainable, paper-backed researcher discovery.",
};

export default async function MentorsPage({
  searchParams,
}: {
  searchParams: Promise<{ mode?: string; query?: string }>;
}) {
  const { mode, query } = await searchParams;
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Derive real researcher candidates from OpenAlex papers, inspect every relevance contribution, and keep unverifiable employment or availability claims explicitly unknown."
          eyebrow="Step 3 · Evidence"
          title="Understand the evidence behind every connection"
        />
        <WorkflowSteps current="Evidence" />
        <div className="mt-8">
          <MentorModeExperience
            initialMode={mode === "demo" ? "demo" : "live"}
            initialQuery={query}
          />
        </div>
      </Container>
    </main>
  );
}
