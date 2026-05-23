import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  AdminFeedbackGroup,
  AdminFeedbackGroupDetailResponse,
  AdminFeedbackTriageOverlay,
} from "../api/types";

vi.mock("../api/client", () => ({
  fetchAdminFeedbackGroups: vi.fn(),
  fetchAdminFeedbackGroupDetail: vi.fn(),
  fetchAdminFeedbackTriage: vi.fn(),
  saveAdminFeedbackTriage: vi.fn(),
  fetchDevFixtures: vi.fn(),
  fetchFreshness: vi.fn(),
  fetchHealth: vi.fn(),
  fetchRoutes: vi.fn(),
  postQuery: vi.fn(),
  postQueryFeedback: vi.fn(),
  postStructuredQuery: vi.fn(),
}));

import AdminFeedbackPage from "../AdminFeedbackPage";
import {
  fetchAdminFeedbackGroupDetail,
  fetchAdminFeedbackGroups,
  fetchAdminFeedbackTriage,
  saveAdminFeedbackTriage,
} from "../api/client";
import { resolveRootView } from "../main";

function makeOverlay(
  overrides: Partial<AdminFeedbackTriageOverlay> = {},
): AdminFeedbackTriageOverlay {
  return {
    schema_version: 1,
    group_id: "qfg_123",
    review_status: "new",
    triage_decision: null,
    review_notes: "",
    linked_case_or_issue: "",
    reviewer_source: null,
    updated_at: null,
    source_record_ids: ["qfb_1"],
    ...overrides,
  };
}

function makeGroup(overrides: Partial<AdminFeedbackGroup> = {}): AdminFeedbackGroup {
  return {
    group_id: "qfg_123",
    count: 2,
    first_seen: "2026-05-22T00:00:00Z",
    last_seen: "2026-05-23T00:00:00Z",
    representative_query: "Jokic personal fouls leaderboard",
    feedback_sources: ["user_submitted"],
    feedback_types: ["expected_supported"],
    routes: ["season_leaders"],
    statuses: ["no_result"],
    reasons: ["filter_not_supported"],
    unsupported_filters: ["personal_foul_leaderboard"],
    user_notes: ["Expected this to work."],
    record_ids: ["qfb_1", "qfb_2"],
    object_keys: ["query_feedback/preview/2026/05/22/qfb_1.json"],
    suggested_triage: "unsupported_family",
    triage_modifiers: [],
    triage_overlay: makeOverlay(),
    review_status: "new",
    triage_decision: null,
    ...overrides,
  };
}

function makeDetail(
  group = makeGroup(),
  overlay = makeOverlay({ group_id: group.group_id }),
): AdminFeedbackGroupDetailResponse {
  return {
    ok: true,
    group,
    records: [
      {
        id: "qfb_1",
        created_at: "2026-05-22T00:00:00Z",
        feedback_source: "user_submitted",
        feedback_type: "expected_supported",
        query: group.representative_query,
        route: "season_leaders",
        status: "no_result",
        reason: "filter_not_supported",
        unsupported_filters: ["personal_foul_leaderboard"],
        user_note: "Expected this to work.",
        notes: [],
        caveats: [],
        answer_text_preview: "",
        error_message: "",
        elapsed_ms: null,
        object_key: "query_feedback/preview/2026/05/22/qfb_1.json",
      },
    ],
    triage_overlay: overlay,
    handoff_summary: "Group: qfg_123",
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  window.history.replaceState(null, "", "/");
  vi.mocked(fetchAdminFeedbackGroups).mockResolvedValue({
    ok: true,
    source_mode: "r2",
    bucket: "nbatools-data",
    prefix: "query_feedback/preview",
    total_found: 2,
    total_exported: 2,
    excluded_smoke_count: 0,
    group_count: 1,
    groups: [makeGroup()],
  });
  vi.mocked(fetchAdminFeedbackGroupDetail).mockImplementation((groupId) =>
    Promise.resolve(makeDetail(makeGroup({ group_id: groupId }))),
  );
  vi.mocked(fetchAdminFeedbackTriage).mockImplementation((groupId) =>
    Promise.resolve({
      ok: true,
      triage_overlay: makeOverlay({ group_id: groupId }),
    }),
  );
  vi.mocked(saveAdminFeedbackTriage).mockResolvedValue({
    ok: true,
    triage_overlay: makeOverlay({
      review_status: "reviewed",
      triage_decision: "bug",
      review_notes: "Create regression test.",
      linked_case_or_issue: "RAW-123",
      reviewer_source: "admin_feedback_console",
      updated_at: "2026-05-23T12:00:00Z",
    }),
  });
});

describe("AdminFeedbackPage", () => {
  it("routes /admin/feedback to the lazy internal feedback console", async () => {
    render(resolveRootView("/admin/feedback"));

    expect(
      await screen.findByRole("heading", {
        name: "Query Feedback Review Console",
      }),
    ).toBeInTheDocument();
    expect(fetchAdminFeedbackGroups).toHaveBeenCalledTimes(1);
  });

  it("shows an understandable unauthorized token state", async () => {
    vi.mocked(fetchAdminFeedbackGroups).mockRejectedValueOnce(
      new Error("admin_token_required"),
    );

    render(<AdminFeedbackPage />);

    expect(
      await screen.findByText(/requires a token/i),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Admin token")).toBeInTheDocument();
  });

  it("renders mocked feedback groups", async () => {
    render(<AdminFeedbackPage />);

    expect(await screen.findByText("1 groups loaded.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: /Jokic personal fouls leaderboard/i,
      }),
    ).toBeInTheDocument();
  });

  it("loads detail when a group is selected", async () => {
    const second = makeGroup({
      group_id: "qfg_456",
      representative_query: "Celtics bench scoring leaders",
    });
    vi.mocked(fetchAdminFeedbackGroups).mockResolvedValueOnce({
      ok: true,
      source_mode: "r2",
      bucket: "nbatools-data",
      prefix: "query_feedback/preview",
      total_found: 3,
      total_exported: 3,
      excluded_smoke_count: 0,
      group_count: 2,
      groups: [makeGroup(), second],
    });

    render(<AdminFeedbackPage />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: /Celtics bench scoring leaders/i,
      }),
    );

    await waitFor(() =>
      expect(fetchAdminFeedbackGroupDetail).toHaveBeenCalledWith("qfg_456", {
        adminToken: "",
      }),
    );
  });

  it("saves triage overlays without editing source feedback records", async () => {
    render(<AdminFeedbackPage />);

    await screen.findByLabelText("Handoff summary");
    const reviewStatusFields = screen.getAllByLabelText("Review status");
    fireEvent.change(reviewStatusFields[1], {
      target: { value: "reviewed" },
    });
    fireEvent.change(screen.getAllByLabelText("Triage decision")[1], {
      target: { value: "bug" },
    });
    fireEvent.change(screen.getByLabelText("Review notes"), {
      target: { value: "Create regression test." },
    });
    fireEvent.change(screen.getByLabelText("Linked case or issue"), {
      target: { value: "RAW-123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save triage overlay" }));

    await waitFor(() =>
      expect(saveAdminFeedbackTriage).toHaveBeenCalledWith(
        "qfg_123",
        expect.objectContaining({
          review_status: "reviewed",
          triage_decision: "bug",
          review_notes: "Create regression test.",
          linked_case_or_issue: "RAW-123",
          reviewer_source: "admin_feedback_console",
        }),
        { adminToken: "" },
      ),
    );
    expect(
      await screen.findByText(/Original feedback records were not changed/i),
    ).toBeInTheDocument();
  });

  it("renders a copyable handoff summary for the selected group", async () => {
    render(<AdminFeedbackPage />);

    const summary = (await screen.findByLabelText(
      "Handoff summary",
    )) as HTMLTextAreaElement;
    expect(summary.value).toContain("group_id: qfg_123");
    expect(summary.value).toContain(
      "unsupported_filters: personal_foul_leaderboard",
    );
    expect(
      screen.getByRole("button", { name: "Copy handoff summary" }),
    ).toBeInTheDocument();
  });

  it("applies filters through the list request state", async () => {
    render(<AdminFeedbackPage />);

    await screen.findByText("1 groups loaded.");
    fireEvent.change(screen.getAllByLabelText("Review status")[0], {
      target: { value: "deferred" },
    });
    fireEvent.change(screen.getByLabelText("Route"), {
      target: { value: "season_leaders" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() =>
      expect(fetchAdminFeedbackGroups).toHaveBeenLastCalledWith(
        expect.objectContaining({
          review_status: "deferred",
          route: "season_leaders",
        }),
        { adminToken: "" },
      ),
    );
  });
});
