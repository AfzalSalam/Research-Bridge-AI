export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
}

export type HealthResult =
  | {
      state: "available";
      data: HealthResponse;
    }
  | {
      state: "unavailable";
      message: string;
    };

interface HealthRequestOptions {
  baseUrl?: string;
  signal?: AbortSignal;
}

const DEFAULT_API_BASE_URL = "http://localhost:8000";
const HEALTH_REQUEST_TIMEOUT_MS = 3_000;

function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;

  return (
    candidate.status === "ok" &&
    typeof candidate.service === "string" &&
    typeof candidate.version === "string" &&
    typeof candidate.environment === "string"
  );
}

function withoutTrailingSlash(value: string): string {
  return value.replace(/\/$/, "");
}

export async function getApiHealth(
  options: HealthRequestOptions = {},
): Promise<HealthResult> {
  const baseUrl = withoutTrailingSlash(
    options.baseUrl ?? process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL,
  );

  try {
    const response = await fetch(`${baseUrl}/api/v1/health`, {
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
      signal: options.signal ?? AbortSignal.timeout(HEALTH_REQUEST_TIMEOUT_MS),
    });

    if (!response.ok) {
      return {
        state: "unavailable",
        message: `The API returned HTTP ${response.status}.`,
      };
    }

    const payload: unknown = await response.json();

    if (!isHealthResponse(payload)) {
      return {
        state: "unavailable",
        message: "The API returned an unexpected health response.",
      };
    }

    return {
      state: "available",
      data: payload,
    };
  } catch {
    return {
      state: "unavailable",
      message: "The API could not be reached from the frontend server.",
    };
  }
}
