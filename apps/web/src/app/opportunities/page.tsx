import type { Metadata } from "next";

import { RouteShell } from "@/components/layout/route-shell";

export const metadata: Metadata = {
  title: "Research Opportunities",
  description: "The future verified research opportunity workspace.",
};

export default function OpportunitiesPage() {
  return (
    <RouteShell
      description="Find research internships and lab opportunities without converting guesses into facts."
      eyebrow="Opportunities"
      plannedItems={[
        "Verified source URL and last-checked timestamp",
        "Unknown funding, mode, and availability shown honestly",
        "Saved opportunities with clear provenance",
      ]}
      stateDescription="Opportunity ingestion and verification arrive after the core discovery workflow. No unverified listings are shown here."
      stateTitle="No verified opportunities are available"
      title="Research openings you can verify"
    />
  );
}
