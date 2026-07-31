import type {
  MentorCandidate,
  OutreachDraft,
  PaperEvidence,
  StudentProfile,
} from "@/features/demo/contracts";

interface BuildDraftInput {
  mentor: MentorCandidate;
  papers: PaperEvidence[];
  profile: StudentProfile;
  now?: () => Date;
}

function paperConnection(
  paper: PaperEvidence,
  profile: StudentProfile,
): string {
  if (paper.evidenceStrength === "title-only") {
    return `I found the title of your ${paper.year} paper, “${paper.title},” relevant to my interest in ${paper.topics[0]}. Because only title-level metadata is available in this demo, I would be interested in learning more about the work.`;
  }

  return `I was particularly interested in your ${paper.year} paper, “${paper.title}.” Its focus on ${paper.topics.slice(0, 2).join(" and ")} connects with the way I have been thinking about ${profile.researchInterests[0]}.`;
}

export function buildEvidenceGroundedDraft({
  mentor,
  now = () => new Date(),
  papers,
  profile,
}: BuildDraftInput): OutreachDraft {
  if (papers.length === 0) {
    throw new Error("At least one paper is required to build an outreach draft.");
  }

  const paperParagraphs = papers
    .map((paper) => paperConnection(paper, profile))
    .join("\n\n");

  return {
    id: `draft-${mentor.id}`,
    mentorId: mentor.id,
    paperIds: papers.map((paper) => paper.id),
    subject: `Prospective student interested in ${mentor.researchThemes[0]}`,
    body: `Dear ${mentor.name.replace(" (fictional)", "")},

I am ${profile.name}, a ${profile.program} at ${profile.institution}. My interests include ${profile.researchInterests.join(", ")}.

${paperParagraphs}

For my project, “${profile.projectTitle},” I ${profile.projectSummary.charAt(0).toLowerCase()}${profile.projectSummary.slice(1)} I can currently commit ${profile.weeklyAvailability} each week.

If this direction is relevant to your current work, I would value the opportunity to ask a few focused questions about possible student research contributions. I understand that availability and funding have not been verified.

Thank you for your time,
${profile.name}`,
    generatedAt: now().toISOString(),
    mode: "deterministic-demo",
    templateVersion: "phase-03.v1",
    evidenceLinks: [mentor.sourceUrl, ...papers.map((paper) => paper.sourceUrl)],
  };
}
