import { z } from "zod";

import {
  type DemoBootstrapResponse as GeneratedDemoBootstrapResponse,
  type DiscoveryRequest as GeneratedDiscoveryRequest,
  type OutreachDraftRequest as GeneratedOutreachDraftRequest,
  type StudentProfile as GeneratedStudentProfile,
  Sdk,
} from "@/lib/api/generated";
import { client } from "@/lib/api/generated/client.gen";
import {
  apiErrorResponseSchema,
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

client.setConfig({ baseUrl: "/backend" });
const sdk = new Sdk({ client });

export class DemoApiError extends Error {
  readonly code: string;
  readonly details: ReadonlyArray<{ field: string; message: string; type: string }>;
  readonly requestId: string | null;
  readonly status: number | null;

  constructor({
    code,
    details = [],
    message,
    requestId = null,
    status = null,
  }: {
    code: string;
    details?: ReadonlyArray<{ field: string; message: string; type: string }>;
    message: string;
    requestId?: string | null;
    status?: number | null;
  }) {
    super(message);
    this.name = "DemoApiError";
    this.code = code;
    this.details = details;
    this.requestId = requestId;
    this.status = status;
  }
}

interface ApiResult<T> {
  data: T | undefined;
  error: unknown;
  response?: Response;
}

function requestIdFrom(response?: Response): string | null {
  return response?.headers.get("X-Request-ID") ?? null;
}

function parseData<T>(
  result: ApiResult<unknown>,
  schema: z.ZodType<T>,
): T {
  if (result.data !== undefined) {
    const parsed = schema.safeParse(result.data);
    if (parsed.success) return parsed.data;
    throw new DemoApiError({
      code: "contract_mismatch",
      message: "The API returned data that does not match the checked contract.",
      requestId: requestIdFrom(result.response),
      status: result.response?.status ?? null,
    });
  }

  const parsedError = apiErrorResponseSchema.safeParse(result.error);
  if (parsedError.success) {
    throw new DemoApiError({
      code: parsedError.data.error.code,
      details: parsedError.data.error.details,
      message: parsedError.data.error.message,
      requestId: parsedError.data.error.requestId,
      status: result.response?.status ?? null,
    });
  }

  throw new DemoApiError({
    code: "network_error",
    message: "The demo API could not be reached.",
    requestId: requestIdFrom(result.response),
    status: result.response?.status ?? null,
  });
}

export async function getDemoBootstrap(signal?: AbortSignal): Promise<DemoBootstrap> {
  const result = await sdk.readDemoBootstrapApiV1DemoBootstrapGet({ signal });
  const bootstrap = parseData(result, demoBootstrapSchema);
  return bootstrap satisfies GeneratedDemoBootstrapResponse;
}

export async function updateDemoProfile(
  profile: StudentProfile,
  signal?: AbortSignal,
): Promise<StudentProfile> {
  const body = profile satisfies GeneratedStudentProfile;
  const result = await sdk.updateDemoProfileApiV1DemoProfilePut({ body, signal });
  return parseData(result, studentProfileSchema);
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
  return parseData(result, discoveryResponseSchema);
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
  return parseData(result, outreachDraftSchema);
}
