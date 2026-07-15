import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { postQueryFeedback } from "../api/client";
import type { FeedbackType, QueryResponse } from "../api/types";
import { Button, type ButtonVariant } from "../design-system";
import {
  buildQueryErrorFeedbackPayload,
  buildQueryFeedbackPayload,
} from "./queryFeedbackPayload";
import styles from "./QueryFeedback.module.css";

type FeedbackOption = {
  value: FeedbackType;
  label: string;
};

const SUCCESS_OPTIONS: FeedbackOption[] = [
  { value: "wrong_answer", label: "This answer looks wrong" },
  { value: "confusing_answer", label: "This is confusing" },
  { value: "ui_issue", label: "There is a UI issue" },
  { value: "other", label: "Other" },
];

const REVIEW_OPTIONS: FeedbackOption[] = [
  { value: "expected_supported", label: "I expected this to work" },
  { value: "no_result", label: "No matching result seems wrong" },
  { value: "confusing_answer", label: "This is confusing" },
  { value: "other", label: "Other" },
];

const ERROR_OPTIONS: FeedbackOption[] = [
  { value: "error", label: "Report this error" },
  { value: "expected_supported", label: "I expected this to work" },
  { value: "ui_issue", label: "There is a UI issue" },
  { value: "other", label: "Other" },
];

interface QueryFeedbackButtonProps {
  data?: QueryResponse;
  query?: string;
  errorMessage?: string | null;
  defaultFeedbackType: FeedbackType;
  triggerLabel: string;
  title: string;
  variant?: ButtonVariant;
}

export function QueryFeedbackButton({
  data,
  query,
  errorMessage,
  defaultFeedbackType,
  triggerLabel,
  title,
  variant = "ghost",
}: QueryFeedbackButtonProps) {
  const [open, setOpen] = useState(false);
  const [feedbackType, setFeedbackType] =
    useState<FeedbackType>(defaultFeedbackType);
  const [note, setNote] = useState("");
  const [pending, setPending] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusKind, setStatusKind] = useState<"success" | "error" | null>(null);
  const submissionIdRef = useRef<string | null>(null);

  const options = useMemo(
    () => optionSet(defaultFeedbackType),
    [defaultFeedbackType],
  );

  useEffect(() => {
    setFeedbackType(defaultFeedbackType);
  }, [defaultFeedbackType]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setStatusMessage(null);
    setStatusKind(null);

    const submissionId = submissionIdRef.current ?? crypto.randomUUID();
    submissionIdRef.current = submissionId;
    const basePayload = data
      ? buildQueryFeedbackPayload(data, feedbackType, note)
      : buildQueryErrorFeedbackPayload({
          query: query ?? "",
          errorMessage,
          feedbackSource: "user_submitted",
          feedbackType,
          note,
        });
    const payload = { ...basePayload, submission_id: submissionId };

    try {
      const response = await postQueryFeedback(payload);
      if (!response.stored) {
        throw new Error("Feedback storage is disabled.");
      }
      setOpen(false);
      setNote("");
      setFeedbackType(defaultFeedbackType);
      submissionIdRef.current = null;
      setStatusKind("success");
      setStatusMessage("Thanks. This query was saved for review.");
    } catch {
      setStatusKind("error");
      setStatusMessage(
        "Could not submit the report. Your query result is unchanged.",
      );
    } finally {
      setPending(false);
    }
  }

  function handleCancel() {
    if (pending) return;
    setOpen(false);
    setNote("");
    setFeedbackType(defaultFeedbackType);
    submissionIdRef.current = null;
  }

  return (
    <div className={styles.feedback}>
      <Button
        type="button"
        variant={variant}
        size="sm"
        onClick={() => {
          setStatusMessage(null);
          setStatusKind(null);
          submissionIdRef.current = null;
          setOpen(true);
        }}
      >
        {triggerLabel}
      </Button>

      {statusMessage && (
        <div
          className={[
            styles.status,
            statusKind === "success" ? styles.success : styles.failure,
          ]
            .filter(Boolean)
            .join(" ")}
          role={statusKind === "error" ? "alert" : "status"}
        >
          {statusMessage}
        </div>
      )}

      {open && (
        <div className={styles.backdrop}>
          <div
            className={styles.dialog}
            role="dialog"
            aria-modal="true"
            aria-labelledby="query-feedback-title"
            data-shortcut-scope="ignore"
          >
            <form className={styles.form} onSubmit={handleSubmit}>
              <div className={styles.header}>
                <div>
                  <div className={styles.eyebrow}>Query feedback</div>
                  <h2 id="query-feedback-title" className={styles.title}>
                    {title}
                  </h2>
                </div>
              </div>

              <fieldset className={styles.optionGroup}>
                <legend className={styles.legend}>Feedback type</legend>
                {options.map((option) => (
                  <label key={option.value} className={styles.option}>
                    <input
                      type="radio"
                      name="feedback_type"
                      value={option.value}
                      checked={feedbackType === option.value}
                      onChange={() => setFeedbackType(option.value)}
                    />
                    <span>{option.label}</span>
                  </label>
                ))}
              </fieldset>

              <label className={styles.noteField}>
                <span>Optional note</span>
                <textarea
                  value={note}
                  maxLength={1000}
                  onChange={(event) => setNote(event.currentTarget.value)}
                  rows={4}
                />
              </label>

              <div className={styles.privacy}>
                Do not include personal information.
              </div>

              <div className={styles.actions}>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={handleCancel}
                  disabled={pending}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary" size="sm" loading={pending}>
                  Submit
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function optionSet(defaultFeedbackType: FeedbackType): FeedbackOption[] {
  if (defaultFeedbackType === "error") return ERROR_OPTIONS;
  if (
    defaultFeedbackType === "no_result" ||
    defaultFeedbackType === "expected_supported" ||
    defaultFeedbackType === "unsupported"
  ) {
    return REVIEW_OPTIONS;
  }
  return SUCCESS_OPTIONS;
}
