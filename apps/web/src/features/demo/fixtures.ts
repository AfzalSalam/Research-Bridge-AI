import {
  demoStateSchema,
  mentorCandidateSchema,
  opportunitySchema,
  type DemoState,
  type MentorCandidate,
  type Opportunity,
  type StudentProfile,
} from "@/features/demo/contracts";

export const DEMO_DISCOVERY_QUERY =
  "human-centred machine learning for low-resource health systems";

export const demoProfile: StudentProfile = {
  id: "demo-student",
  name: "Aarav Demo",
  program: "B.Tech in Computer Science, fourth year",
  institution: "Riverview College of Engineering (fictional)",
  graduationYear: "2027",
  researchInterests: [
    "human-centred AI",
    "low-resource machine learning",
    "digital health",
  ],
  skills: ["Python", "PyTorch", "FastAPI", "research prototyping"],
  projectTitle: "Uncertainty-aware triage interface for community clinics",
  projectSummary:
    "Built a classroom prototype that surfaces model uncertainty and lets healthcare workers record when local context disagrees with a prediction.",
  weeklyAvailability: "10-15 hours",
};

const mentorFixtures: MentorCandidate[] = [
  {
    id: "mentor-mira-sen",
    name: "Dr. Mira Sen (fictional)",
    role: "Associate Professor",
    department: "Human-Centred Computing",
    institution: "Northstar Institute of Technology (fictional)",
    location: "Bengaluru, India (fictional campus)",
    researchThemes: ["human-centred AI", "clinical decision support", "uncertainty"],
    fitRationale: [
      "The selected topic overlaps with the paper themes human-centred AI and clinical decision support.",
      "The demo profile describes an uncertainty-aware interface project, which can support a specific outreach connection.",
    ],
    identityNote:
      "This is one internally consistent fictional author profile; no real-world identity resolution was attempted.",
    sourceUrl: "https://example.org/research-bridge/fictional-mentor-mira-sen",
    papers: [
      {
        id: "paper-context-before-confidence",
        title: "Context Before Confidence: Decision Support for Resource-Constrained Clinics",
        authors: ["Mira Sen", "Jon Bell"],
        year: 2025,
        venue: "Fictional Symposium on Responsible Health AI",
        summary:
          "A fictional abstract describing interfaces that expose uncertainty, missing context, and escalation paths to community health workers.",
        topics: ["clinical decision support", "uncertainty", "human-centred AI"],
        evidenceStrength: "full-abstract",
        sourceUrl: "https://example.org/research-bridge/papers/context-before-confidence",
      },
      {
        id: "paper-feedback-under-shift",
        title: "Field Feedback Under Distribution Shift",
        authors: ["Mira Sen", "Leah Noor"],
        year: 2024,
        venue: "Fictional Workshop on Interactive ML",
        summary:
          "Only fictional title and bibliographic metadata are available in this scenario; technical claims must not be inferred.",
        topics: ["distribution shift", "field feedback"],
        evidenceStrength: "title-only",
        sourceUrl: "https://example.org/research-bridge/papers/feedback-under-shift",
      },
    ],
  },
  {
    id: "mentor-neel-iyer",
    name: "Dr. Neel Iyer (fictional)",
    role: "Assistant Professor",
    department: "Computing for Development",
    institution: "Eastlake Research University (fictional)",
    location: "Pune, India (fictional campus)",
    researchThemes: ["low-resource ML", "participatory evaluation", "mobile health"],
    fitRationale: [
      "The discovery topic and publication metadata share low-resource machine learning and health-system themes.",
      "The profile's research prototyping skill is relevant context, but lab availability remains unknown.",
    ],
    identityNote:
      "This fictional fixture has no ORCID or institutional directory verification; contact and availability are unknown.",
    sourceUrl: "https://example.org/research-bridge/fictional-mentor-neel-iyer",
    papers: [
      {
        id: "paper-participatory-benchmarks",
        title: "Participatory Benchmarks for Low-Connectivity Health Tools",
        authors: ["Neel Iyer", "Samira Das"],
        year: 2025,
        venue: "Fictional Conference on Computing and Society",
        summary:
          "A fictional abstract about evaluating offline-first health tools with practitioners and documenting where aggregate metrics hide workflow failures.",
        topics: ["participatory evaluation", "mobile health", "low connectivity"],
        evidenceStrength: "full-abstract",
        sourceUrl: "https://example.org/research-bridge/papers/participatory-benchmarks",
      },
      {
        id: "paper-compression-community-models",
        title: "Compression Trade-offs in Community-Deployed Models",
        authors: ["Neel Iyer", "Ana Cho"],
        year: 2023,
        venue: "Fictional Systems for Social Impact Review",
        summary:
          "A fictional abstract comparing latency, calibration, and maintainability constraints in models deployed on shared mobile devices.",
        topics: ["model compression", "calibration", "mobile deployment"],
        evidenceStrength: "full-abstract",
        sourceUrl: "https://example.org/research-bridge/papers/compression-community-models",
      },
    ],
  },
  {
    id: "mentor-lina-okafor",
    name: "Dr. Lina Okafor (fictional)",
    role: "Research Faculty",
    department: "Data and Public Systems Lab",
    institution: "Harbour School of Informatics (fictional)",
    location: "Remote collaboration mode unknown",
    researchThemes: ["public-interest technology", "data quality", "health operations"],
    fitRationale: [
      "A retrieved paper discusses data-quality failures in health operations, adjacent to the submitted discovery topic.",
      "This is a broader thematic connection and is intentionally presented after the two closer demo candidates.",
    ],
    identityNote:
      "Affiliation and publication links are fictional examples; funding, work mode, and student openings are unknown.",
    sourceUrl: "https://example.org/research-bridge/fictional-mentor-lina-okafor",
    papers: [
      {
        id: "paper-data-gaps-care-pathways",
        title: "Data Gaps Across Community Care Pathways",
        authors: ["Lina Okafor", "Priya Shah"],
        year: 2024,
        venue: "Fictional Journal of Public Data Systems",
        summary:
          "A fictional abstract mapping missing-data patterns to operational hand-offs without claiming that a predictive model can repair institutional gaps.",
        topics: ["data quality", "health operations", "public systems"],
        evidenceStrength: "full-abstract",
        sourceUrl: "https://example.org/research-bridge/papers/data-gaps-care-pathways",
      },
    ],
  },
];

export const demoMentors = mentorCandidateSchema.array().parse(mentorFixtures);

const opportunityFixtures: Opportunity[] = [
  {
    id: "opp-northstar-hcai",
    title: "Student Research Assistant - Human-Centred AI",
    organisation: "Northstar Institute of Technology (fictional)",
    location: "Bengaluru, India (fictional campus)",
    mode: "Hybrid",
    funding: "Unknown",
    availability: "Open",
    deadline: "2027-01-20",
    description:
      "A fictional term-time role supporting interview synthesis and prototype evaluation for clinical decision-support interfaces.",
    topics: ["human-centred AI", "digital health"],
    sourceUrl: "https://example.org/research-bridge/opportunities/northstar-hcai",
    lastVerifiedAt: "2026-07-28T10:00:00.000Z",
  },
  {
    id: "opp-eastlake-mobile-health",
    title: "Research Internship - Offline Mobile Health",
    organisation: "Eastlake Research University (fictional)",
    location: "Pune, India (fictional campus)",
    mode: "On-site",
    funding: "Funded",
    availability: "Unknown",
    deadline: null,
    description:
      "A fictional summer research listing focused on evaluation tooling for low-connectivity mobile health deployments.",
    topics: ["mobile health", "low-resource ML"],
    sourceUrl: "https://example.org/research-bridge/opportunities/eastlake-mobile-health",
    lastVerifiedAt: "2026-07-27T08:30:00.000Z",
  },
  {
    id: "opp-harbour-public-data",
    title: "Capstone Collaboration - Public Data Quality",
    organisation: "Harbour School of Informatics (fictional)",
    location: "Location unknown",
    mode: "Unknown",
    funding: "Unfunded",
    availability: "Open",
    deadline: "2026-12-05",
    description:
      "A fictional capstone brief investigating how missing operational data affects community-care hand-offs.",
    topics: ["data quality", "public-interest technology"],
    sourceUrl: "https://example.org/research-bridge/opportunities/harbour-public-data",
    lastVerifiedAt: "2026-07-24T13:15:00.000Z",
  },
];

export const demoOpportunities = opportunitySchema.array().parse(opportunityFixtures);

export function createInitialDemoState(): DemoState {
  return demoStateSchema.parse({
    schemaVersion: 1,
    profile: demoProfile,
    discovery: {
      query: "",
      scenario: "complete",
      status: "idle",
      stage: 0,
      mentorIds: [],
      errorMessage: null,
    },
    selectedMentorId: null,
    selectedPaperIds: {},
    drafts: [],
    savedOpportunityIds: [],
    applications: [],
  });
}

export function findDemoMentor(mentorId: string | null) {
  return demoMentors.find((mentor) => mentor.id === mentorId);
}

export function findDemoOpportunity(opportunityId: string) {
  return demoOpportunities.find((opportunity) => opportunity.id === opportunityId);
}
