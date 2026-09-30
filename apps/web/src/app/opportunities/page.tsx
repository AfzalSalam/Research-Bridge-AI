import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { LiveOpportunities } from "@/features/opportunities/live-opportunities";

export const metadata: Metadata = {
  title: "Research Opportunities",
  description: "Verified, source-linked research opportunities with explicit unknowns.",
};

export default function OpportunitiesPage() {
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Browse verified research openings from employer-published boards. Every listing retains its source URL. Funding, work mode, and availability are never guessed."
          eyebrow="Step 3 · Opportunities"
          title="Research openings you can verify"
        />
        <div className="mt-8">
          <LiveOpportunities />
        </div>
      </Container>
    </main>
  );
}
