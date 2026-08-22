import type { OpportunitySearchResponse } from "@/features/opportunities/contracts";

export const completeOpportunityResponse: OpportunitySearchResponse = {
  query: "machine learning",
  results: [
    {
      id: "30000000-0000-4000-8000-000000000001",
      sourceName: "Greenhouse",
      sourceKind: "official-ats",
      sourceRecordId: "thealleninstitute:7366273",
      evidenceConfidence: "high",
      opportunityType: "internship",
      title: "Research Internship, Robotics",
      organisation: "Allen Institute for AI (Ai2)",
      descriptionExcerpt: "Machine learning research for embodied robotics.",
      researchFields: ["Robotics"],
      duration: "12 weeks",
      eligibility: "Undergraduate students with research experience.",
      countryCode: "US",
      location: "Seattle, WA",
      workMode: "unclear",
      funding: "unclear",
      availability: "open",
      deadline: null,
      sourceUrl:
        "https://job-boards.greenhouse.io/thealleninstitute/jobs/7366273",
      applicationUrl:
        "https://job-boards.greenhouse.io/thealleninstitute/jobs/7366273",
      sourceUpdatedAt: "2026-07-30T16:00:00Z",
      lastVerifiedAt: "2026-08-01T12:00:00Z",
      isStale: false,
      isExpired: false,
      extractionEvidence: [
        {
          field: "inclusion",
          value: "opportunity-title-signals.v1:research-internship",
        },
      ],
      inclusionSignal: "research-internship",
      isSaved: false,
      applicationId: null,
    },
  ],
  sources: [
    {
      key: "thealleninstitute",
      organisation: "Allen Institute for AI (Ai2)",
      status: "success",
      acceptedCount: 1,
      invalidCount: 0,
      errorCode: null,
      retryable: false,
    },
  ],
  partialFailure: false,
  policyVersion: "opportunity-title-signals.v1",
  retrievedAt: "2026-08-01T12:00:00Z",
  rankingApplied: false,
};
