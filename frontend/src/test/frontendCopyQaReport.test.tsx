import fs from "node:fs";
import { describe, expect, it } from "vitest";
import {
  buildFrontendCopyReport,
  defaultCorpusPath,
  loadBackendQaRecords,
  loadFrontendCopyCorpus,
  repoRoot,
  writeFrontendCopyReport,
} from "./frontendCopyQaHarness";

const WRITE_REPORT = process.env.FRONTEND_COPY_QA_WRITE === "1";

describe("frontend copy QA report harness", () => {
  it("loads the selected frontend-copy corpus", () => {
    const corpus = loadFrontendCopyCorpus();

    expect(corpus.version).toBe(1);
    expect(corpus.source_backend_run).toBe(
      "outputs/raw_query_answer_qa/20260517T070422Z/report.jsonl",
    );
    expect(corpus.cases.length).toBe(125);
    expect(corpus.cases[0]).toMatchObject({
      id: "celtics_record_playoff_teams",
      category: "team_record",
    });
  });

  it("matches every selected case to the backend QA JSONL", () => {
    const corpus = loadFrontendCopyCorpus();
    const backendRecords = loadBackendQaRecords(
      `${repoRoot()}/${corpus.source_backend_run}`,
    );
    const missingIds = corpus.cases
      .map((entry) => entry.id)
      .filter((caseId) => !backendRecords.has(caseId));

    expect(missingIds).toEqual([]);
  });

  it("renders representative cases and extracts core copy fields", () => {
    const report = buildFrontendCopyReport({
      runId: "frontend-copy-qa-test",
      generatedAt: "2026-05-14T00:00:00.000Z",
      caseIds: [
        "celtics_record_playoff_teams",
        "centers_rebound_leaders_wave4",
        "most_points_last_night",
      ],
    });

    expect(report.selected_case_count).toBe(3);
    expect(report.render_failures).toBe(0);

    const teamRecord = report.cases.find(
      (entry) => entry.case_id === "celtics_record_playoff_teams",
    );
    expect(teamRecord?.render_status).toBe("rendered");
    expect(teamRecord?.frontend?.hero_text).toBeTruthy();
    expect(teamRecord?.frontend?.tables[0]?.headers.length).toBeGreaterThan(0);

    const noResult = report.cases.find(
      (entry) => entry.case_id === "most_points_last_night",
    );
    expect(noResult?.render_status).toBe("rendered");
    expect(noResult?.frontend?.no_result?.title).toBeTruthy();
    expect(noResult?.frontend?.no_result?.message).toBeTruthy();
  });

  it(
    "writes frontend-copy report artifacts when explicitly enabled",
    () => {
      if (!WRITE_REPORT) {
        expect(fs.existsSync(defaultCorpusPath())).toBe(true);
        return;
      }

      const report = buildFrontendCopyReport();
      const paths = writeFrontendCopyReport(report);

      expect(report.selected_case_count).toBe(125);
      expect(report.rendered_successfully).toBe(125);
      expect(report.render_failures).toBe(0);
      expect(report.missing_backend_records).toBe(0);
      expect(report.soft_check_summary.fail).toBe(0);
      expect(report.soft_check_summary.not_checked).toBe(0);
      expect(fs.existsSync(paths.jsonl_path)).toBe(true);
      expect(fs.existsSync(paths.markdown_path)).toBe(true);
      expect(fs.existsSync(paths.summary_path)).toBe(true);
    },
    30_000,
  );
});
