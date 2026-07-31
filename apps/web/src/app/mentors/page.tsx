import type { Metadata } from "next";

import { RouteShell } from "@/components/layout/route-shell";

export const metadata: Metadata = {
  title: "Research Mentors",
  description: "The future professor evidence and matching workspace.",
};

export default function MentorsPage() {
  return (
    <RouteShell
      description="Review professor candidates through publications, affiliations, identifiers, and transparent match evidence."
      eyebrow="Mentors"
      plannedItems={[
        "Professor identity resolution with ambiguity surfaced",
        "Publication-level evidence and source provenance",
        "Deterministic matching added only after retrieval quality is measured",
      ]}
      stateDescription="Professor records and matching are intentionally absent until the underlying academic evidence pipeline is trustworthy."
      stateTitle="No professor evidence has been retrieved"
      title="Understand the researcher before the match"
    />
  );
}
