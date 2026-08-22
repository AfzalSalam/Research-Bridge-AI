import type {
  ApplicationCreateRequest,
  ApplicationUpdateRequest,
} from "@/lib/api/generated";
import { Sdk } from "@/lib/api/generated";
import { client } from "@/lib/api/generated/client.gen";
import {
  applicationListResponseSchema,
  applicationResponseSchema,
  type ApplicationResponse,
  type ApplicationStatus,
} from "@/features/applications/contracts";
import { parseApiData } from "@/lib/api/result";

client.setConfig({ baseUrl: "/backend" });
const sdk = new Sdk({ client });

export async function createLiveApplication({
  opportunityId,
}: {
  opportunityId: string;
}): Promise<ApplicationResponse> {
  const body = { opportunityId } satisfies ApplicationCreateRequest;
  const result = await sdk.createApplicationApiV1ApplicationsPost({ body });
  return parseApiData(result, applicationResponseSchema);
}

export async function listLiveApplications({
  signal,
}: {
  signal?: AbortSignal;
} = {}): Promise<ApplicationResponse[]> {
  const result = await sdk.listApplicationsApiV1ApplicationsGet({ signal });
  return parseApiData(result, applicationListResponseSchema).items;
}

export async function updateLiveApplication({
  applicationId,
  expectedVersion,
  followUpDate,
  notes,
  status,
}: {
  applicationId: string;
  expectedVersion: number;
  followUpDate: string | null;
  notes: string;
  status: ApplicationStatus;
}): Promise<ApplicationResponse> {
  const body = {
    expectedVersion,
    followUpDate,
    notes,
    status,
  } satisfies ApplicationUpdateRequest;
  const result = await sdk.updateApplicationApiV1ApplicationsApplicationIdPut({
    body,
    path: { application_id: applicationId },
  });
  return parseApiData(result, applicationResponseSchema);
}
