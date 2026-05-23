import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  fetchAdminFeedbackGroupDetail,
  fetchAdminFeedbackGroups,
  fetchAdminFeedbackTriage,
  saveAdminFeedbackTriage,
} from "./api/client";
import type {
  AdminFeedbackFilters,
  AdminFeedbackGroup,
  AdminFeedbackGroupDetailResponse,
  AdminFeedbackReviewStatus,
  AdminFeedbackTriageDecision,
  AdminFeedbackTriageOverlay,
} from "./api/types";
import CopyButton from "./components/CopyButton";
import styles from "./AdminFeedbackPage.module.css";

const REVIEW_STATUSES: AdminFeedbackReviewStatus[] = [
  "new",
  "reviewed",
  "deferred",
  "closed",
];

const TRIAGE_DECISIONS: AdminFeedbackTriageDecision[] = [
  "bug",
  "support_candidate",
  "expected_unsupported",
  "duplicate",
  "no_action",
  "needs_more_data",
  "parser_routing_risk",
  "ui_copy_issue",
];

const DEFAULT_REVIEWER_SOURCE = "admin_feedback_console";

interface TriageFormState {
  review_status: AdminFeedbackReviewStatus;
  triage_decision: "" | AdminFeedbackTriageDecision;
  review_notes: string;
  linked_case_or_issue: string;
  reviewer_source: string;
}

function safeErrorMessage(error: unknown): string {
  const raw = error instanceof Error ? error.message : String(error ?? "");
  const firstLine = raw.split(/\r?\n/)[0]?.trim();
  if (!firstLine) return "Request failed.";
  return firstLine.length > 240 ? `${firstLine.slice(0, 237)}...` : firstLine;
}

function isUnauthorized(errorMessage: string): boolean {
  return /admin_token_required|unauthorized|HTTP 401/i.test(errorMessage);
}

function isDisabled(errorMessage: string): boolean {
  return /admin_feedback_disabled|HTTP 404/i.test(errorMessage);
}

function listText(values: string[] | undefined): string {
  return values?.filter(Boolean).join(", ") || "none";
}

function formFromOverlay(overlay?: AdminFeedbackTriageOverlay): TriageFormState {
  return {
    review_status: overlay?.review_status ?? "new",
    triage_decision: overlay?.triage_decision ?? "",
    review_notes: overlay?.review_notes ?? "",
    linked_case_or_issue: overlay?.linked_case_or_issue ?? "",
    reviewer_source: overlay?.reviewer_source ?? DEFAULT_REVIEWER_SOURCE,
  };
}

function buildHandoffSummary(
  detail: AdminFeedbackGroupDetailResponse,
  overlay: AdminFeedbackTriageOverlay | null,
): string {
  const group = detail.group;
  const currentOverlay = overlay ?? detail.triage_overlay;
  const userNotes = group.user_notes.length
    ? group.user_notes.map((note) => `- ${note}`).join("\n")
    : "none";

  return [
    `group_id: ${group.group_id}`,
    `representative_query: ${group.representative_query || "none"}`,
    `count: ${group.count}`,
    `route/status/reason: ${listText(group.routes)} / ${listText(group.statuses)} / ${listText(group.reasons)}`,
    `unsupported_filters: ${listText(group.unsupported_filters)}`,
    `feedback_types: ${listText(group.feedback_types)}`,
    `feedback_sources: ${listText(group.feedback_sources)}`,
    `user_notes:\n${userNotes}`,
    `suggested_triage: ${group.suggested_triage || "none"}`,
    `current_saved_decision: ${currentOverlay?.review_status ?? "new"} / ${currentOverlay?.triage_decision ?? "none"}`,
    `review_notes: ${currentOverlay?.review_notes || "none"}`,
    `linked_case_or_issue: ${currentOverlay?.linked_case_or_issue || "none"}`,
  ].join("\n");
}

function DetailValue({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className={styles.detailCard}>
      <h3>{title}</h3>
      {children}
    </section>
  );
}

export default function AdminFeedbackPage() {
  const [adminToken, setAdminToken] = useState("");
  const [draftFilters, setDraftFilters] = useState<AdminFeedbackFilters>({});
  const [appliedFilters, setAppliedFilters] = useState<AdminFeedbackFilters>({});
  const [groups, setGroups] = useState<AdminFeedbackGroup[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [detail, setDetail] =
    useState<AdminFeedbackGroupDetailResponse | null>(null);
  const [triageOverlay, setTriageOverlay] =
    useState<AdminFeedbackTriageOverlay | null>(null);
  const [triageForm, setTriageForm] = useState<TriageFormState>(() =>
    formFromOverlay(),
  );
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadGroups() {
      setListLoading(true);
      setError(null);
      setSaveMessage(null);
      try {
        const data = await fetchAdminFeedbackGroups(appliedFilters, {
          adminToken,
        });
        if (cancelled) return;
        setGroups(data.groups);
        setListLoading(false);
        setSelectedGroupId((current) => {
          if (current && data.groups.some((group) => group.group_id === current)) {
            return current;
          }
          return data.groups[0]?.group_id ?? null;
        });
      } catch (loadError) {
        if (cancelled) return;
        setGroups([]);
        setDetail(null);
        setTriageOverlay(null);
        setListLoading(false);
        setError(safeErrorMessage(loadError));
      }
    }

    void loadGroups();
    return () => {
      cancelled = true;
    };
  }, [adminToken, appliedFilters]);

  useEffect(() => {
    if (!selectedGroupId) {
      setDetail(null);
      setTriageOverlay(null);
      setTriageForm(formFromOverlay());
      return;
    }

    const groupId = selectedGroupId;
    let cancelled = false;

    async function loadDetail() {
      setDetailLoading(true);
      setError(null);
      setSaveMessage(null);
      try {
        const [detailData, triageData] = await Promise.all([
          fetchAdminFeedbackGroupDetail(groupId, { adminToken }),
          fetchAdminFeedbackTriage(groupId, { adminToken }),
        ]);
        if (cancelled) return;
        setDetail(detailData);
        setTriageOverlay(triageData.triage_overlay);
        setTriageForm(formFromOverlay(triageData.triage_overlay));
        setDetailLoading(false);
      } catch (loadError) {
        if (cancelled) return;
        setDetail(null);
        setTriageOverlay(null);
        setDetailLoading(false);
        setError(safeErrorMessage(loadError));
      }
    }

    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [adminToken, selectedGroupId]);

  const selectedGroup = useMemo(
    () => groups.find((group) => group.group_id === selectedGroupId) ?? null,
    [groups, selectedGroupId],
  );
  const handoffSummary = detail
    ? buildHandoffSummary(detail, triageOverlay)
    : "";
  const needsToken = error ? isUnauthorized(error) : false;
  const disabled = error ? isDisabled(error) : false;

  function updateDraftFilter(key: keyof AdminFeedbackFilters, value: string) {
    setDraftFilters((current) => ({
      ...current,
      [key]: value || undefined,
    }));
  }

  function applyFilters() {
    setAppliedFilters(draftFilters);
  }

  async function saveTriage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedGroupId) return;

    setSaving(true);
    setError(null);
    setSaveMessage(null);
    try {
      const response = await saveAdminFeedbackTriage(
        selectedGroupId,
        {
          review_status: triageForm.review_status,
          triage_decision: triageForm.triage_decision || null,
          review_notes: triageForm.review_notes,
          linked_case_or_issue: triageForm.linked_case_or_issue,
          reviewer_source:
            triageForm.reviewer_source.trim() || DEFAULT_REVIEWER_SOURCE,
        },
        { adminToken },
      );
      setTriageOverlay(response.triage_overlay);
      setTriageForm(formFromOverlay(response.triage_overlay));
      setGroups((current) =>
        current.map((group) =>
          group.group_id === selectedGroupId
            ? {
                ...group,
                triage_overlay: response.triage_overlay,
                review_status: response.triage_overlay.review_status,
                triage_decision: response.triage_overlay.triage_decision,
              }
            : group,
        ),
      );
      setSaveMessage("Triage overlay saved. Original feedback records were not changed.");
    } catch (saveError) {
      setError(safeErrorMessage(saveError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <header className={styles.header}>
          <p className={styles.eyebrow}>Internal Admin</p>
          <h1 className={styles.title}>Query Feedback Review Console</h1>
          <p className={styles.lede}>
            Review grouped query feedback, inspect immutable source records, and
            save mutable triage overlays. This console does not edit parser
            rules, QA corpora, result contracts, or the original feedback stream.
          </p>
        </header>

        <section className={styles.panel} aria-label="Admin access">
          <div className={styles.field}>
            <label htmlFor="admin-token">Admin token</label>
            <input
              id="admin-token"
              type="password"
              value={adminToken}
              placeholder="Paste token when the API requires one"
              onChange={(event) => setAdminToken(event.target.value)}
            />
          </div>
          {needsToken ? (
            <p className={styles.error}>
              The admin feedback API requires a token. Paste the token above to
              retry with X-NBATools-Admin-Token.
            </p>
          ) : null}
          {disabled ? (
            <p className={styles.error}>
              The admin feedback API is disabled. Enable
              NBATOOLS_ADMIN_FEEDBACK_ENABLED before using this console.
            </p>
          ) : null}
        </section>

        <section className={styles.panel} aria-label="Feedback filters">
          <div className={styles.filters}>
            <div className={styles.field}>
              <label htmlFor="review-status-filter">Review status</label>
              <select
                id="review-status-filter"
                value={draftFilters.review_status ?? ""}
                onChange={(event) =>
                  updateDraftFilter("review_status", event.target.value)
                }
              >
                <option value="">Any</option>
                {REVIEW_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </div>
            <div className={styles.field}>
              <label htmlFor="triage-filter">Triage decision</label>
              <select
                id="triage-filter"
                value={draftFilters.triage_decision ?? ""}
                onChange={(event) =>
                  updateDraftFilter("triage_decision", event.target.value)
                }
              >
                <option value="">Any</option>
                {TRIAGE_DECISIONS.map((decision) => (
                  <option key={decision} value={decision}>
                    {decision}
                  </option>
                ))}
              </select>
            </div>
            <div className={styles.field}>
              <label htmlFor="feedback-source-filter">Feedback source</label>
              <select
                id="feedback-source-filter"
                value={draftFilters.feedback_source ?? ""}
                onChange={(event) =>
                  updateDraftFilter("feedback_source", event.target.value)
                }
              >
                <option value="">Any</option>
                <option value="automatic">automatic</option>
                <option value="user_submitted">user_submitted</option>
              </select>
            </div>
            <div className={styles.field}>
              <label htmlFor="feedback-type-filter">Feedback type</label>
              <select
                id="feedback-type-filter"
                value={draftFilters.feedback_type ?? ""}
                onChange={(event) =>
                  updateDraftFilter("feedback_type", event.target.value)
                }
              >
                <option value="">Any</option>
                <option value="wrong_answer">wrong_answer</option>
                <option value="expected_supported">expected_supported</option>
                <option value="confusing_answer">confusing_answer</option>
                <option value="no_result">no_result</option>
                <option value="unsupported">unsupported</option>
                <option value="error">error</option>
                <option value="ui_issue">ui_issue</option>
                <option value="other">other</option>
              </select>
            </div>
            <div className={styles.field}>
              <label htmlFor="route-filter">Route</label>
              <input
                id="route-filter"
                value={draftFilters.route ?? ""}
                onChange={(event) => updateDraftFilter("route", event.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="status-filter">Status</label>
              <input
                id="status-filter"
                value={draftFilters.status ?? ""}
                onChange={(event) =>
                  updateDraftFilter("status", event.target.value)
                }
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="reason-filter">Reason</label>
              <input
                id="reason-filter"
                value={draftFilters.reason ?? ""}
                onChange={(event) =>
                  updateDraftFilter("reason", event.target.value)
                }
              />
            </div>
          </div>
          <div className={styles.actions}>
            <button className={styles.button} type="button" onClick={applyFilters}>
              Apply filters
            </button>
          </div>
        </section>

        {error && !needsToken && !disabled ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}

        {listLoading ? (
          <section className={styles.panel} aria-busy="true">
            Loading feedback groups...
          </section>
        ) : (
          <div className={styles.layout}>
            <section className={styles.panel} aria-label="Feedback groups">
              <h2>Grouped feedback</h2>
              <p className={styles.status}>{groups.length} groups loaded.</p>
              {groups.length === 0 ? (
                <p className={styles.muted}>No feedback groups match the current filters.</p>
              ) : (
                <div className={styles.groupList}>
                  {groups.map((group) => (
                    <button
                      key={group.group_id}
                      type="button"
                      className={styles.groupButton}
                      aria-pressed={group.group_id === selectedGroupId}
                      onClick={() => setSelectedGroupId(group.group_id)}
                    >
                      <span className={styles.groupTitle}>
                        {group.representative_query || group.group_id}
                      </span>
                      <span className={styles.groupMeta}>
                        {group.count} records · {group.review_status ?? "new"} ·{" "}
                        {group.triage_decision ?? "no decision"}
                      </span>
                      <span className={styles.pillRow}>
                        <span className={styles.pill}>{listText(group.routes)}</span>
                        <span className={styles.pill}>{listText(group.statuses)}</span>
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className={styles.panel} aria-label="Selected group detail">
              <h2>Selected group detail</h2>
              {detailLoading ? <p aria-busy="true">Loading group detail...</p> : null}
              {!selectedGroup ? (
                <p className={styles.muted}>Select a feedback group to review.</p>
              ) : null}
              {detail && selectedGroup ? (
                <>
                  <div className={styles.detailGrid}>
                    <DetailValue title="Representative query">
                      <p>{selectedGroup.representative_query || "none"}</p>
                    </DetailValue>
                    <DetailValue title="Volume">
                      <p>
                        {selectedGroup.count} records · first seen{" "}
                        {selectedGroup.first_seen || "unknown"} · last seen{" "}
                        {selectedGroup.last_seen || "unknown"}
                      </p>
                    </DetailValue>
                    <DetailValue title="Route / status / reason">
                      <p>
                        {listText(selectedGroup.routes)} /{" "}
                        {listText(selectedGroup.statuses)} /{" "}
                        {listText(selectedGroup.reasons)}
                      </p>
                    </DetailValue>
                    <DetailValue title="Unsupported filters">
                      <p>{listText(selectedGroup.unsupported_filters)}</p>
                    </DetailValue>
                    <DetailValue title="Sources and types">
                      <p>
                        {listText(selectedGroup.feedback_sources)} /{" "}
                        {listText(selectedGroup.feedback_types)}
                      </p>
                    </DetailValue>
                    <DetailValue title="Suggested triage">
                      <p>{selectedGroup.suggested_triage || "none"}</p>
                    </DetailValue>
                    <DetailValue title="Current overlay">
                      <p>
                        {triageOverlay?.review_status ?? "new"} /{" "}
                        {triageOverlay?.triage_decision ?? "no decision"}
                      </p>
                      <p className={styles.muted}>
                        Updated {triageOverlay?.updated_at ?? "not saved"}
                      </p>
                    </DetailValue>
                    <DetailValue title="User notes">
                      {selectedGroup.user_notes.length ? (
                        <ul>
                          {selectedGroup.user_notes.map((note) => (
                            <li key={note}>{note}</li>
                          ))}
                        </ul>
                      ) : (
                        <p>none</p>
                      )}
                    </DetailValue>
                  </div>

                  <form className={styles.panel} onSubmit={saveTriage}>
                    <h3>Triage editor</h3>
                    <div className={styles.filters}>
                      <div className={styles.field}>
                        <label htmlFor="review-status">Review status</label>
                        <select
                          id="review-status"
                          value={triageForm.review_status}
                          onChange={(event) =>
                            setTriageForm((current) => ({
                              ...current,
                              review_status: event.target
                                .value as AdminFeedbackReviewStatus,
                            }))
                          }
                        >
                          {REVIEW_STATUSES.map((status) => (
                            <option key={status} value={status}>
                              {status}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className={styles.field}>
                        <label htmlFor="triage-decision">Triage decision</label>
                        <select
                          id="triage-decision"
                          value={triageForm.triage_decision}
                          onChange={(event) =>
                            setTriageForm((current) => ({
                              ...current,
                              triage_decision: event.target
                                .value as TriageFormState["triage_decision"],
                            }))
                          }
                        >
                          <option value="">No decision</option>
                          {TRIAGE_DECISIONS.map((decision) => (
                            <option key={decision} value={decision}>
                              {decision}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className={styles.field}>
                        <label htmlFor="linked-case">Linked case or issue</label>
                        <input
                          id="linked-case"
                          value={triageForm.linked_case_or_issue}
                          onChange={(event) =>
                            setTriageForm((current) => ({
                              ...current,
                              linked_case_or_issue: event.target.value,
                            }))
                          }
                        />
                      </div>
                      <div className={styles.field}>
                        <label htmlFor="reviewer-source">Reviewer source</label>
                        <input
                          id="reviewer-source"
                          value={triageForm.reviewer_source}
                          onChange={(event) =>
                            setTriageForm((current) => ({
                              ...current,
                              reviewer_source: event.target.value,
                            }))
                          }
                        />
                      </div>
                    </div>
                    <div className={styles.field}>
                      <label htmlFor="review-notes">Review notes</label>
                      <textarea
                        id="review-notes"
                        rows={4}
                        value={triageForm.review_notes}
                        onChange={(event) =>
                          setTriageForm((current) => ({
                            ...current,
                            review_notes: event.target.value,
                          }))
                        }
                      />
                    </div>
                    <div className={styles.actions}>
                      <button
                        className={styles.button}
                        type="submit"
                        disabled={saving}
                      >
                        {saving ? "Saving..." : "Save triage overlay"}
                      </button>
                      {saveMessage ? (
                        <span className={styles.status}>{saveMessage}</span>
                      ) : null}
                    </div>
                  </form>

                  <section className={styles.detailCard}>
                    <h3>Handoff summary</h3>
                    <textarea
                      className={styles.summaryBox}
                      readOnly
                      value={handoffSummary}
                      aria-label="Handoff summary"
                    />
                    <div className={styles.actions}>
                      <CopyButton text={handoffSummary} label="Copy handoff summary" />
                    </div>
                  </section>
                </>
              ) : null}
            </section>
          </div>
        )}
      </div>
    </main>
  );
}
