import type { OutreachDraftResponse } from "@/features/outreach/contracts";

export const completeOutreachDraftResponse: OutreachDraftResponse = {
  id: "20000000-0000-4000-8000-000000000001",
  mentorId: "10000000-0000-4000-8000-000000000002",
  recipientDisplayName: "Mira Sen",
  recipientContact: null,
  recipientSourceUrl: "https://openalex.org/A1000000001",
  recipientLastVerifiedAt: "2026-08-01T16:00:00Z",
  subject: "Question about evidence-centred clinical AI research",
  body:
    "Dear Mira Sen,\n\nI am Aarav Demo, a B.Tech student interested in human-centred AI.\n\nI appreciated the evidence boundary in your paper.\n\nWould you be open to a brief conversation about a focused student contribution?\n\nThank you for your time,\nAarav Demo",
  selectedStudentFacts: [
    { key: "profile.name", label: "Name", value: "Aarav Demo" },
    {
      key: "profile.program",
      label: "Degree program",
      value: "B.Tech in Computer Science",
    },
  ],
  selectedPapers: [
    {
      id: "10000000-0000-4000-8000-000000000001",
      title: "Human-centred AI for clinical decisions",
      publicationYear: 2026,
      venue: "Journal of Responsible Health AI",
      evidenceStrength: "full-abstract",
      sourceUrl: "https://openalex.org/W1000000001",
      lastVerifiedAt: "2026-08-01T16:00:00Z",
    },
  ],
  claimEvidence: [
    {
      claim:
        "I am Aarav Demo, a B.Tech student interested in human-centred AI.",
      references: [
        {
          type: "student-fact",
          id: "profile.name",
          label: "Name",
          sourceUrl: null,
        },
      ],
    },
    {
      claim: "I appreciated the evidence boundary in your paper.",
      references: [
        {
          type: "paper",
          id: "10000000-0000-4000-8000-000000000001",
          label: "Human-centred AI for clinical decisions",
          sourceUrl: "https://openalex.org/W1000000001",
        },
      ],
    },
  ],
  uncertaintyWarnings: [
    "Recipient contact details, availability, and funding are unknown.",
    "This draft is prepared for human review and cannot be sent by Research Bridge AI.",
  ],
  evidenceMapStatus: "verified-generated",
  generation: {
    mode: "deterministic",
    provider: null,
    model: null,
    promptVersion: null,
    templateVersion: "outreach-template.v1",
    fallbackReason: "provider-not-configured",
  },
  draftVersion: 1,
  revisions: [
    {
      version: 1,
      evidenceMapStatus: "verified-generated",
      createdAt: "2026-08-01T17:00:00Z",
    },
  ],
  createdAt: "2026-08-01T17:00:00Z",
  updatedAt: "2026-08-01T17:00:00Z",
  canSend: false,
};
