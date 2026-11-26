export class ApiRequestError extends Error {
  readonly code: string;
  readonly status?: number;
  readonly requestId?: string;
  readonly retryAfterSeconds?: number;

  constructor(
    message: string,
    code: string,
    status?: number,
    requestId?: string,
    retryAfterSeconds?: number,
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.code = code;
    this.status = status;
    this.requestId = requestId;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export function retryAfterSeconds(value: string | null | undefined): number | undefined {
  if (!value?.trim()) return undefined;
  if (/^\d+$/.test(value)) {
    const seconds = Number(value);
    return Number.isSafeInteger(seconds) ? seconds : undefined;
  }
  const time = Date.parse(value);
  return Number.isFinite(time)
    ? Math.max(0, Math.ceil((time - Date.now()) / 1000))
    : undefined;
}
