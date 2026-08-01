import { z } from "zod";

const apiErrorResponseSchema = z.object({
  error: z.object({
    code: z.string().min(1),
    message: z.string().min(1),
    requestId: z.string().min(1),
    details: z.array(
      z.object({
        field: z.string(),
        message: z.string().min(1),
        type: z.string().min(1),
      }),
    ),
  }),
});

export class ApiError extends Error {
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
    this.name = "ApiError";
    this.code = code;
    this.details = details;
    this.requestId = requestId;
    this.status = status;
  }
}

export interface ApiResult<T> {
  data: T | undefined;
  error: unknown;
  response?: Response;
}

function requestIdFrom(response?: Response): string | null {
  return response?.headers.get("X-Request-ID") ?? null;
}

export function parseApiData<T>(
  result: ApiResult<unknown>,
  schema: z.ZodType<T>,
): T {
  if (result.data !== undefined) {
    const parsed = schema.safeParse(result.data);
    if (parsed.success) return parsed.data;
    throw new ApiError({
      code: "contract_mismatch",
      message: "The API returned data that does not match the checked contract.",
      requestId: requestIdFrom(result.response),
      status: result.response?.status ?? null,
    });
  }

  const parsedError = apiErrorResponseSchema.safeParse(result.error);
  if (parsedError.success) {
    throw new ApiError({
      code: parsedError.data.error.code,
      details: parsedError.data.error.details,
      message: parsedError.data.error.message,
      requestId: parsedError.data.error.requestId,
      status: result.response?.status ?? null,
    });
  }

  throw new ApiError({
    code: "network_error",
    message: "The Research Bridge API could not be reached.",
    requestId: requestIdFrom(result.response),
    status: result.response?.status ?? null,
  });
}
