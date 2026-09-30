import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { LiveApplications } from "@/features/applications/live-applications";

export const metadata: Metadata = {
  title: "Application Tracker",
  description: "Track your research applications with explicit status history and follow-up dates.",
};

export default function ApplicationsPage() {
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Keep notes, follow-up dates, and an explicit status history for every research opportunity you are pursuing. Nothing is auto-submitted — you stay in control."
          eyebrow="Step 4 · Track"
          title="Keep every research conversation accountable"
        />
        <div className="mt-8">
          <LiveApplications />
        </div>
      </Container>
    </main>
  );
}
