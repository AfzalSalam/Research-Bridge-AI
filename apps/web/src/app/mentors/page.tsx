import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { LiveMentorDiscovery } from "@/features/mentors/live-mentor-discovery";

export const metadata: Metadata = {
  title: "Research Mentors",
  description: "Discover professors backed by real paper evidence, with transparent relevance scores.",
};

export default async function MentorsPage({
  searchParams,
}: {
  searchParams: Promise<{ query?: string }>;
}) {
  const { query } = await searchParams;
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Discover professors whose published work aligns with your research interests. Every match is backed by real OpenAlex papers — availability, funding, and contact details are never guessed."
          eyebrow="Step 2 · Mentors"
          title="Find researchers who publish what you care about"
        />
        <div className="mt-8">
          <LiveMentorDiscovery initialQuery={query} />
        </div>
      </Container>
    </main>
  );
}
