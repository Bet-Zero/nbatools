import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { QueryResponse } from "../api/types";
import { postQueryFeedback } from "../api/client";
import { QueryFeedbackButton } from "../components/QueryFeedback";
import { defaultFeedbackTypeForResult } from "../components/queryFeedbackPayload";
import ResultRenderer from "../components/results/ResultRenderer";

vi.mock("../api/client", () => ({
  postQueryFeedback: vi.fn(),
}));

function makeResponse(overrides: Partial<QueryResponse> = {}): QueryResponse {
  return {
    ok: true,
    query: "Jokic last 10 games",
    route: "player_game_summary",
    result_status: "ok",
    result_reason: null,
    current_through: "2026-04-28",
    confidence: 0.92,
    intent: "player_summary",
    alternates: [],
    notes: [],
    caveats: [],
    result: {
      query_class: "summary",
      result_status: "ok",
      metadata: {
        route: "player_game_summary",
        player: "Nikola Jokic",
        answer_phrase: "Nikola Jokic averaged 25 points.",
      },
      notes: [],
      caveats: [],
      sections: {
        summary: [{ player_name: "Nikola Jokic", pts_avg: 25 }],
      },
      current_through: "2026-04-28",
    },
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  window.history.replaceState(null, "", "/");
  vi.mocked(postQueryFeedback).mockResolvedValue({
    ok: true,
    feedback_id: "qfb_test",
    stored: true,
    disabled: false,
  });
});

describe("QueryFeedbackButton", () => {
  it("renders a compact report dialog", () => {
    render(
      <QueryFeedbackButton
        data={makeResponse()}
        defaultFeedbackType="wrong_answer"
        triggerLabel="Report issue"
        title="Report an issue with this answer"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Report issue" }));

    expect(
      screen.getByRole("dialog", {
        name: "Report an issue with this answer",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/stored raw feedback expires within 90 days/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Do not include personal information/)).toBeInTheDocument();
  });

  it("traps focus, closes on Escape, and restores the trigger", async () => {
    render(
      <QueryFeedbackButton
        data={makeResponse()}
        defaultFeedbackType="wrong_answer"
        triggerLabel="Report issue"
        title="Report an issue with this answer"
      />,
    );

    const trigger = screen.getByRole("button", { name: "Report issue" });
    fireEvent.click(trigger);

    const firstOption = screen.getByRole("radio", {
      name: "This answer looks wrong",
    });
    await waitFor(() => expect(firstOption).toHaveFocus());

    const submit = screen.getByRole("button", { name: "Submit" });
    submit.focus();
    fireEvent.keyDown(submit, { key: "Tab" });
    expect(firstOption).toHaveFocus();

    fireEvent.keyDown(firstOption, { key: "Tab", shiftKey: true });
    expect(submit).toHaveFocus();

    fireEvent.keyDown(submit, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });

  it("submits successful-answer feedback through the API client", async () => {
    render(
      <QueryFeedbackButton
        data={makeResponse()}
        defaultFeedbackType="wrong_answer"
        triggerLabel="Report issue"
        title="Report an issue with this answer"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Report issue" }));
    fireEvent.change(screen.getByLabelText("Optional note"), {
      target: { value: "The average looks off." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => expect(postQueryFeedback).toHaveBeenCalledTimes(1));
    expect(postQueryFeedback).toHaveBeenCalledWith(
      expect.objectContaining({
        query: "Jokic last 10 games",
        feedback_source: "user_submitted",
        feedback_type: "wrong_answer",
        route: "player_game_summary",
        status: "ok",
        reason: null,
        user_note: "The average looks off.",
        answer_text_preview: "Nikola Jokic averaged 25 points.",
        metadata: expect.objectContaining({
          route: "player_game_summary",
          status: "ok",
          reason: null,
          query_class: "summary",
          confidence: 0.92,
          intent: "player_summary",
          current_through: "2026-04-28",
        }),
      }),
    );
    expect(
      await screen.findByText(/Receipt: qfb_test/),
    ).toBeInTheDocument();
  });

  it("submits no-result review feedback from the no-result display", async () => {
    const data = makeResponse({
      ok: false,
      route: null,
      result_status: "no_result",
      result_reason: "no_match",
      result: {
        query_class: "unknown",
        result_status: "no_result",
        result_reason: "no_match",
        metadata: {
          unsupported_filters: ["personal_foul_leaderboard"],
        },
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    render(
      <ResultRenderer
        data={data}
        feedbackAction={
          <QueryFeedbackButton
            data={data}
            defaultFeedbackType={defaultFeedbackTypeForResult(data)}
            triggerLabel="Submit for review"
            title="Expected this to work?"
          />
        }
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Submit for review" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => expect(postQueryFeedback).toHaveBeenCalledTimes(1));
    expect(postQueryFeedback).toHaveBeenCalledWith(
      expect.objectContaining({
        query: "Jokic last 10 games",
        feedback_type: "no_result",
        status: "no_result",
        reason: "no_match",
        metadata: expect.objectContaining({
          unsupported_filters: ["personal_foul_leaderboard"],
          status: "no_result",
          reason: "no_match",
          query_class: "unknown",
        }),
      }),
    );
  });

  it("does not render feedback controls when no feedback action is supplied", () => {
    const data = makeResponse({
      ok: false,
      route: null,
      result_status: "no_result",
      result_reason: "unsupported",
      result: {
        query_class: "unknown",
        result_status: "no_result",
        result_reason: "unsupported",
        metadata: {},
        notes: [],
        caveats: [],
        sections: {},
      },
    });

    render(<ResultRenderer data={data} displayMode="review" />);

    expect(
      screen.queryByRole("button", { name: "Submit for review" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Report issue" }),
    ).not.toBeInTheDocument();
  });

  it("shows a non-blocking failure message when feedback submit fails", async () => {
    vi.mocked(postQueryFeedback).mockRejectedValueOnce(new Error("offline"));
    render(
      <QueryFeedbackButton
        data={makeResponse()}
        defaultFeedbackType="wrong_answer"
        triggerLabel="Report issue"
        title="Report an issue with this answer"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Report issue" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    expect(
      await screen.findByText(
        "Could not submit the report. Your query result is unchanged.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("reuses one submission ID for a user-triggered retry", async () => {
    vi.mocked(postQueryFeedback)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({
        ok: true,
        feedback_id: "qfb_retry",
        stored: true,
        disabled: false,
      });
    render(
      <QueryFeedbackButton
        data={makeResponse()}
        defaultFeedbackType="wrong_answer"
        triggerLabel="Report issue"
        title="Report an issue with this answer"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Report issue" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));
    await screen.findByText(
      "Could not submit the report. Your query result is unchanged.",
    );
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));
    await screen.findByText(/Receipt: qfb_retry/);

    const first = vi.mocked(postQueryFeedback).mock.calls[0][0].submission_id;
    const second = vi.mocked(postQueryFeedback).mock.calls[1][0].submission_id;
    expect(first).toMatch(/^[0-9a-f-]{36}$/);
    expect(second).toBe(first);
  });
});
