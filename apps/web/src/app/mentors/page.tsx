import { SelectedAuthor } from "@/features/research/selected-author";
import type { Metadata } from "next";

import { Container } from "@/components/layout/container";
import { PageHeader } from "@/components/layout/page-header";
import { LiveMentorDiscovery } from "@/features/mentors/live-mentor-discovery";

export const metadata: Metadata = {
  title: "Find Professors",
  description: "Discover professors backed by real paper evidence, with transparent relevance scores.",
};

export default async function MentorsPage({
  searchParams,
}: {
  searchParams: Promise<{ query?: string; paper?: string; author?: string }>;
}) {
  const { query, paper, author } = await searchParams;
  return (
    <main id="main-content">
      <Container className="py-10 sm:py-14 lg:py-16">
        <PageHeader
          description="Explore people who wrote papers on your topic. Open a shared paper to see its authors together, then select a person to review their work and prepare an email. Academic roles and openings may be unverified."
          eyebrow="Step 2 · People"
          title="Find Professors"
        />
        <div className="mt-8">
          {paper && author ? <SelectedAuthor paperId={paper} authorId={author}/> : <LiveMentorDiscovery initialQuery={query} />}
        </div>
      </Container>
    </main>
  );
}
