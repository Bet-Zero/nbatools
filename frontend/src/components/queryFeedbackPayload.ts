import type {
  FeedbackSource,
  FeedbackType,
  QueryFeedbackPayload,
  QueryResponse,
} from "../api/types";

export function defaultFeedbackTypeForResult(data: QueryResponse): FeedbackType {
  if (data.result_status === "error") return "error";
  if (
    data.result_reason === "unsupported" ||
    data.result_reason === "filter_not_supported" ||
    data.result_reason === "unrouted"
  ) {
    return "expected_supported";
  }
  if (data.result_status === "no_result") return "no_result";
  return "wrong_answer";
}

export function buildQueryFeedbackPayload(
  data: QueryResponse,
  feedbackType: FeedbackType,
  note = "",
): QueryFeedbackPayload {
  const metadata: Record<string, unknown> = data.result?.metadata ?? {};
  return {
    query: data.query,
    feedback_source: "user_submitted",
    feedback_type: feedbackType,
    source_page: currentSourcePage(),
    route: data.route,
    status: data.result_status,
    reason: data.result_reason,
    result_shape: resultShape(data),
    metadata: {
      ...metadata,
      route: data.route,
      status: data.result_status,
      reason: data.result_reason,
      intent: data.intent,
      confidence: data.confidence,
      current_through: data.current_through,
      query_class: data.result?.query_class,
    },
    notes: [...data.notes, ...(data.result?.notes ?? [])],
    caveats: [...data.caveats, ...(data.result?.caveats ?? [])],
    user_note: note,
    answer_text_preview: answerPreview(data),
  };
}

export function buildQueryErrorFeedbackPayload({
  query,
  errorMessage,
  feedbackSource,
  feedbackType = "error",
  note = "",
}: {
  query: string;
  errorMessage?: string | null;
  feedbackSource: FeedbackSource;
  feedbackType?: FeedbackType;
  note?: string;
}): QueryFeedbackPayload {
  return {
    query,
    feedback_source: feedbackSource,
    feedback_type: feedbackType,
    source_page: currentSourcePage(),
    status: "error",
    reason: "frontend_request_error",
    user_note: note,
    error_message: errorMessage ?? "Request failed.",
  };
}

function resultShape(data: QueryResponse) {
  const sections = data.result?.sections ?? {};
  return {
    query_class: data.result?.query_class,
    section_keys: Object.keys(sections),
    section_row_counts: Object.fromEntries(
      Object.entries(sections).map(([key, rows]) => [
        key,
        Array.isArray(rows) ? rows.length : 0,
      ]),
    ),
  };
}

function answerPreview(data: QueryResponse): string | null {
  const metadata: Record<string, unknown> = data.result?.metadata ?? {};
  const answer =
    textValue(metadata.answer_phrase) ?? textValue(metadata.count_phrase);
  if (answer) return answer;
  const notes = [...data.notes, ...(data.result?.notes ?? [])].filter(Boolean);
  return notes.length ? notes.slice(0, 2).join(" ") : null;
}

function textValue(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed || null;
}

function currentSourcePage(): string {
  if (typeof window === "undefined") return "/";
  return window.location.pathname || "/";
}
