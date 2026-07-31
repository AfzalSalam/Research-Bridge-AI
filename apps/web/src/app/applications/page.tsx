import type { Metadata } from "next";

import { RouteShell } from "@/components/layout/route-shell";

export const metadata: Metadata = {
  title: "Application Tracker",
  description: "The future research application tracking workspace.",
};

export default function ApplicationsPage() {
  return (
    <RouteShell
      description="Track deliberate, human-reviewed outreach from saved candidate to final outcome."
      eyebrow="Applications"
      plannedItems={[
        "Explicit application status transitions",
        "Editable outreach drafts with evidence references",
        "No automatic or mass email sending",
      ]}
      stateDescription="The tracker will begin once saved entities and outreach drafts have durable backend records."
      stateTitle="You have not tracked any applications"
      title="Keep every research conversation accountable"
    />
  );
}
