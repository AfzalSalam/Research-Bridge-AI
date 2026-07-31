import type { Metadata } from "next";

import { RouteShell } from "@/components/layout/route-shell";

export const metadata: Metadata = {
  title: "Research Profile",
  description: "The future evidence-backed student research profile workspace.",
};

export default function ProfilePage() {
  return (
    <RouteShell
      description="Build the verified student context that future matching and outreach will be allowed to use."
      eyebrow="Profile"
      plannedItems={[
        "Research interests and preferred academic domains",
        "Verified education, projects, skills, and availability",
        "Private resume handling with explicit consent",
      ]}
      stateDescription="The responsive profile boundary is ready. Typed fields, validation, persistence, and privacy controls belong to the profile phase."
      stateTitle="No profile form has been implemented yet"
      title="Your research profile, grounded in facts"
    />
  );
}
