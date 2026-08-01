import {
  type DemoBootstrapResponse as GeneratedDemoBootstrapResponse,
  type DiscoveryRequest as GeneratedDiscoveryRequest,
  type OutreachDraftRequest as GeneratedOutreachDraftRequest,
  type StudentProfile as GeneratedStudentProfile,
  Sdk,
} from "@/lib/api/generated";
import { client } from "@/lib/api/generated/client.gen";
import {
  demoBootstrapSchema,
  discoveryResponseSchema,
  outreachDraftSchema,
  studentProfileSchema,
  type DemoBootstrap,
  type DiscoveryResponse,
  type DiscoveryScenario,
  type OutreachDraft,
  type StudentProfile,
} from "@/features/demo/contracts";
import { ApiError, parseApiData } from "@/lib/api/result";

client.setConfig({ baseUrl: "/backend" });
const sdk = new Sdk({ client });

export { ApiError as DemoApiError };

export async function getDemoBootstrap(signal?: AbortSignal): Promise<DemoBootstrap> {
  const result = await sdk.readDemoBootstrapApiV1DemoBootstrapGet({ signal });
  const bootstrap = parseApiData(result, demoBootstrapSchema);
  return bootstrap satisfies GeneratedDemoBootstrapResponse;
}

export async function updateDemoProfile(
  profile: StudentProfile,
  signal?: AbortSignal,
): Promise<StudentProfile> {
  const body = profile satisfies GeneratedStudentProfile;
  const result = await sdk.updateDemoProfileApiV1DemoProfilePut({ body, signal });
  return parseApiData(result, studentProfileSchema);
}

export async function runDemoDiscovery({
  query,
  scenario,
  signal,
}: {
  query: string;
  scenario: DiscoveryScenario;
  signal?: AbortSignal;
}): Promise<DiscoveryResponse> {
  const body = { query, scenario } satisfies GeneratedDiscoveryRequest;
  const result = await sdk.runDemoDiscoveryApiV1DemoDiscoveryPost({ body, signal });
  return parseApiData(result, discoveryResponseSchema);
}

export async function createDemoOutreachDraft({
  mentorId,
  paperIds,
  profile,
  signal,
}: {
  mentorId: string;
  paperIds: string[];
  profile: StudentProfile;
  signal?: AbortSignal;
}): Promise<OutreachDraft> {
  const body = {
    mentorId,
    paperIds,
    profile,
  } satisfies GeneratedOutreachDraftRequest;
  const result = await sdk.createDemoOutreachDraftApiV1DemoOutreachDraftsPost({
    body,
    signal,
  });
  return parseApiData(result, outreachDraftSchema);
}
