import type {
  Application,
  ApplicationStatus,
  DemoState,
  DiscoveryScenario,
  OutreachDraft,
  StudentProfile,
} from "@/features/demo/contracts";

export type DemoAction =
  | { type: "initialize"; profile: StudentProfile }
  | { type: "hydrate"; state: DemoState }
  | { type: "save-profile"; profile: StudentProfile }
  | { type: "start-discovery"; query: string; scenario: DiscoveryScenario }
  | { type: "advance-discovery"; stage: number }
  | {
      type: "finish-discovery";
      status: "complete" | "partial" | "empty" | "error";
      mentorIds: string[];
      errorMessage?: string;
    }
  | { type: "select-mentor"; mentorId: string | null }
  | { type: "toggle-paper"; mentorId: string; paperId: string }
  | { type: "save-draft"; draft: OutreachDraft }
  | { type: "toggle-opportunity"; opportunityId: string }
  | { type: "track-application"; application: Application }
  | {
      type: "update-application";
      applicationId: string;
      status: ApplicationStatus;
      notes: string;
      followUpDate: string | null;
      changedAt: string;
    }
  | { type: "reset"; profile: StudentProfile };

export function createInitialDemoState(profile: StudentProfile): DemoState {
  return {
    schemaVersion: 1,
    profile,
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
  };
}

export function demoReducer(
  state: DemoState | null,
  action: DemoAction,
): DemoState | null {
  if (action.type === "initialize") {
    return createInitialDemoState(action.profile);
  }
  if (action.type === "hydrate") {
    return action.state;
  }
  if (state === null) {
    return null;
  }

  switch (action.type) {
    case "save-profile":
      return { ...state, profile: action.profile };
    case "start-discovery":
      return {
        ...state,
        discovery: {
          query: action.query,
          scenario: action.scenario,
          status: "searching",
          stage: 0,
          mentorIds: [],
          errorMessage: null,
        },
      };
    case "advance-discovery":
      return {
        ...state,
        discovery: { ...state.discovery, stage: action.stage },
      };
    case "finish-discovery":
      return {
        ...state,
        discovery: {
          ...state.discovery,
          status: action.status,
          stage: 3,
          mentorIds: action.mentorIds,
          errorMessage: action.errorMessage ?? null,
        },
      };
    case "select-mentor":
      return { ...state, selectedMentorId: action.mentorId };
    case "toggle-paper": {
      const selected = state.selectedPaperIds[action.mentorId] ?? [];
      const next = selected.includes(action.paperId)
        ? selected.filter((id) => id !== action.paperId)
        : [...selected, action.paperId];
      return {
        ...state,
        selectedPaperIds: { ...state.selectedPaperIds, [action.mentorId]: next },
      };
    }
    case "save-draft": {
      const drafts = state.drafts.filter((draft) => draft.id !== action.draft.id);
      return { ...state, drafts: [...drafts, action.draft] };
    }
    case "toggle-opportunity":
      return {
        ...state,
        savedOpportunityIds: state.savedOpportunityIds.includes(action.opportunityId)
          ? state.savedOpportunityIds.filter((id) => id !== action.opportunityId)
          : [...state.savedOpportunityIds, action.opportunityId],
      };
    case "track-application": {
      const applications = state.applications.filter(
        (application) => application.id !== action.application.id,
      );
      return { ...state, applications: [...applications, action.application] };
    }
    case "update-application":
      return {
        ...state,
        applications: state.applications.map((application) => {
          if (application.id !== action.applicationId) return application;

          const statusChanged = application.status !== action.status;
          return {
            ...application,
            status: action.status,
            notes: action.notes,
            followUpDate: action.followUpDate,
            updatedAt: action.changedAt,
            history: statusChanged
              ? [
                  ...application.history,
                  { status: action.status, changedAt: action.changedAt },
                ]
              : application.history,
          };
        }),
      };
    case "reset":
      return createInitialDemoState(action.profile);
  }
}
