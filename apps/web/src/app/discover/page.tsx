import type { Metadata } from "next";

import { RouteShell } from "@/components/layout/route-shell";

export const metadata: Metadata = {
  title: "Discover Research",
  description: "The future academic paper discovery workspace.",
};

export default function DiscoverPage() {
  return (
    <RouteShell
      description="Explore academic work through traceable sources before asking AI to explain or expand anything."
      eyebrow="Discover"
      plannedItems={[
        "Intent-aware academic search with explicit filters",
        "Normalized paper records from approved academic APIs",
        "Source links, identifiers, and partial-failure handling",
      ]}
      stateDescription="The search interface and external API clients will be added in the discovery phase. This placeholder does not pretend that retrieval is active."
      stateTitle="Academic search is not connected yet"
      title="Start with the evidence"
    />
  );
}
