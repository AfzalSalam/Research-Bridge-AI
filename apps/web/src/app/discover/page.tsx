import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { DiscoveryWorkspace } from "@/features/discovery/discovery-workspace";

export const metadata: Metadata = {
  title: "Discover Research",
  description:
    "Search real academic papers and discover professors whose published work aligns with your research interests.",
};

export default function DiscoverPage() {
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Find papers, understand who wrote them, and explore research opportunities. Choose where to search below."
          eyebrow="Step 1 · Discover"
          title="Discover research that interests you"
        />
        <div className="mt-10"><DiscoveryWorkspace /></div>
      </Container>
    </main>
  );
}
