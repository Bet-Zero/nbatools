import { render } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import type { QueryResponse, ResultStatus } from "../api/types";
import ResultEnvelope from "../components/ResultEnvelope";
import ResultRenderer from "../components/results/ResultRenderer";
import { classifyResultShape } from "../components/results/resultShapes";

export interface FrontendCopyCaseConfig {
  id: string;
  category: string;
  review_focus: string[];
  expected_semantic_facts: string[];
  expected_table_header_fragments: string[];
  expected_filter_chip_fragments: string[];
  expected_absent_fragments: string[];
}

export interface FrontendCopyCorpus {
  version: number;
  source_backend_run: string;
  description: string | null;
  cases: FrontendCopyCaseConfig[];
}

export interface BackendQaRecord {
  id?: string;
  category?: string;
  family?: string;
  priority?: string;
  query?: string;
  route?: string | null;
  intent?: string | null;
  query_class?: string | null;
  result_status?: string;
  result_reason?: string | null;
  ok?: boolean;
  shape_hint?: string | null;
  shape_source?: string | null;
  answer_text_policy?: string | null;
  manual_review?: {
    status?: string;
    tags?: string[];
    notes?: string;
  };
  informational_flags?: string[];
  suspicious_flags?: string[];
  verified_outliers?: string[];
  expectation_results?: unknown[];
  metadata?: Record<string, unknown>;
  applied_filters?: unknown[];
  notes?: unknown[];
  caveats?: unknown[];
  sections?: Record<string, Record<string, unknown>[]>;
}

export interface SoftCheckResult {
  kind:
    | "semantic_fact"
    | "table_header_fragment"
    | "filter_chip_fragment"
    | "absent_fragment";
  fragment: string;
  status: "pass" | "fail" | "not_checked";
  haystack: "visible_text" | "table_headers" | "filter_chips";
}

export interface ExtractedTableCopy {
  index: number;
  aria_label: string | null;
  headers: string[];
  first_row: string[];
}

export interface ExtractedNoResultCopy {
  title: string | null;
  message: string | null;
  details: string[];
  suggested_queries: string[];
  next_steps: string[];
}

export interface ExtractedFrontendCopy {
  result_shape_key: string | null;
  result_shape_name: string | null;
  fallback_pattern: boolean;
  full_text: string;
  hero_text: string | null;
  supporting_text: string[];
  envelope_badges: string[];
  context_chips: string[];
  applied_filter_chips: string[];
  envelope_context_items: string[];
  result_headings: string[];
  tables: ExtractedTableCopy[];
  no_result: ExtractedNoResultCopy | null;
  notes_caveats_rendered: string[];
}

export interface FrontendCopyCaseReport {
  case_id: string;
  category: string;
  review_focus: string[];
  source_backend_run: string;
  backend: {
    query: string | null;
    route: string | null;
    status: string | null;
    reason: string | null;
    shape_hint: string | null;
    shape_source: string | null;
    query_class: string | null;
    sections: string[];
    answer_text_policy: string | null;
    manual_review_status: string | null;
    manual_review_tags: string[];
    informational_flags: string[];
    suspicious_flags: string[];
    verified_outliers: string[];
  };
  render_status: "rendered" | "render_failed" | "missing_backend_record";
  render_error: string | null;
  frontend: ExtractedFrontendCopy | null;
  soft_checks: SoftCheckResult[];
  soft_check_summary: {
    pass: number;
    fail: number;
    not_checked: number;
  };
  review_status: "unreviewed";
  review_flags: string[];
  review_notes: string;
}

export interface FrontendCopyReport {
  run_id: string;
  generated_at: string;
  corpus_path: string;
  source_backend_run: string;
  selected_case_count: number;
  rendered_successfully: number;
  render_failures: number;
  missing_backend_records: number;
  soft_check_summary: {
    pass: number;
    fail: number;
    not_checked: number;
  };
  cases_needing_manual_review: string[];
  cases: FrontendCopyCaseReport[];
}

export interface FrontendCopyReportPaths {
  output_dir: string;
  jsonl_path: string;
  markdown_path: string;
  summary_path: string;
}

type ListField =
  | "review_focus"
  | "expected_semantic_facts"
  | "expected_table_header_fragments"
  | "expected_filter_chip_fragments"
  | "expected_absent_fragments";

const LIST_FIELDS = new Set<ListField>([
  "review_focus",
  "expected_semantic_facts",
  "expected_table_header_fragments",
  "expected_filter_chip_fragments",
  "expected_absent_fragments",
]);

const DEFAULT_LISTS = {
  review_focus: [],
  expected_semantic_facts: [],
  expected_table_header_fragments: [],
  expected_filter_chip_fragments: [],
  expected_absent_fragments: [],
};

export function repoRoot(): string {
  let current = process.cwd();
  for (let i = 0; i < 5; i += 1) {
    if (
      fs.existsSync(path.join(current, "qa", "raw_query_answer_corpus.yaml"))
    ) {
      return current;
    }
    current = path.dirname(current);
  }
  return path.resolve(process.cwd(), "..");
}

export function defaultCorpusPath(): string {
  return path.join(repoRoot(), "qa", "frontend_copy_corpus.yaml");
}

export function loadFrontendCopyCorpus(
  corpusPath = defaultCorpusPath(),
): FrontendCopyCorpus {
  const text = fs.readFileSync(corpusPath, "utf8");
  return parseFrontendCopyCorpus(text);
}

export function parseFrontendCopyCorpus(text: string): FrontendCopyCorpus {
  const root: Partial<FrontendCopyCorpus> = {
    description: null,
    cases: [],
  };
  let inCases = false;
  let activeCase: Partial<FrontendCopyCaseConfig> | null = null;
  let activeList: ListField | null = null;

  const finishCase = () => {
    if (!activeCase) return;
    if (!activeCase.id) {
      throw new Error("frontend copy corpus case is missing id");
    }
    root.cases?.push({
      ...DEFAULT_LISTS,
      category: activeCase.category ?? "uncategorized",
      id: activeCase.id,
      review_focus: activeCase.review_focus ?? [],
      expected_semantic_facts: activeCase.expected_semantic_facts ?? [],
      expected_table_header_fragments:
        activeCase.expected_table_header_fragments ?? [],
      expected_filter_chip_fragments:
        activeCase.expected_filter_chip_fragments ?? [],
      expected_absent_fragments: activeCase.expected_absent_fragments ?? [],
    });
  };

  for (const rawLine of text.split(/\r?\n/)) {
    const trimmed = rawLine.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    if (trimmed === "cases:") {
      inCases = true;
      activeList = null;
      continue;
    }

    if (!inCases) {
      const rootMatch = trimmed.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
      if (!rootMatch) continue;
      const [, key, rawValue] = rootMatch;
      if (key === "version") {
        root.version = Number(rawValue);
      } else if (key === "source_backend_run") {
        root.source_backend_run = parseYamlScalar(rawValue);
      } else if (key === "description") {
        root.description = parseYamlScalar(rawValue);
      }
      continue;
    }

    const caseStart = trimmed.match(/^- id:\s*(.*)$/);
    if (caseStart) {
      finishCase();
      activeCase = {
        ...DEFAULT_LISTS,
        id: parseYamlScalar(caseStart[1]),
      };
      activeList = null;
      continue;
    }

    if (!activeCase) continue;

    const listItem = trimmed.match(/^-\s*(.*)$/);
    if (listItem && activeList) {
      const list = activeCase[activeList];
      if (Array.isArray(list)) {
        list.push(parseYamlScalar(listItem[1]));
      }
      continue;
    }

    const fieldMatch = trimmed.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (!fieldMatch) continue;
    const [, key, rawValue] = fieldMatch;
    if (isListField(key)) {
      activeList = key;
      activeCase[activeList] = [];
    } else if (key === "category") {
      activeCase.category = parseYamlScalar(rawValue);
      activeList = null;
    } else {
      activeList = null;
    }
  }

  finishCase();

  if (!root.version) {
    throw new Error("frontend copy corpus is missing version");
  }
  if (!root.source_backend_run) {
    throw new Error("frontend copy corpus is missing source_backend_run");
  }
  if (!root.cases || root.cases.length === 0) {
    throw new Error("frontend copy corpus has no cases");
  }

  const duplicateIds = duplicateValues(root.cases.map((entry) => entry.id));
  if (duplicateIds.length > 0) {
    throw new Error(
      `frontend copy corpus has duplicate case ids: ${duplicateIds.join(", ")}`,
    );
  }

  return root as FrontendCopyCorpus;
}

function isListField(value: string): value is ListField {
  return LIST_FIELDS.has(value as ListField);
}

export function loadBackendQaRecords(
  backendReportPath: string,
): Map<string, BackendQaRecord> {
  const rows = fs
    .readFileSync(backendReportPath, "utf8")
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line) as BackendQaRecord);
  return new Map(
    rows
      .filter((row) => typeof row.id === "string" && row.id.length > 0)
      .map((row) => [row.id as string, row]),
  );
}

export function buildFrontendCopyReport(options: {
  corpusPath?: string;
  backendReportPath?: string;
  runId?: string;
  generatedAt?: string;
  caseIds?: string[];
} = {}): FrontendCopyReport {
  const corpusPath = options.corpusPath ?? defaultCorpusPath();
  const corpus = loadFrontendCopyCorpus(corpusPath);
  const backendReportPath =
    options.backendReportPath ??
    path.join(repoRoot(), corpus.source_backend_run);
  const backendRows = loadBackendQaRecords(backendReportPath);
  const selectedCases = options.caseIds
    ? corpus.cases.filter((entry) => options.caseIds?.includes(entry.id))
    : corpus.cases;
  const runId = options.runId ?? createRunId();
  const generatedAt = options.generatedAt ?? new Date().toISOString();
  const sourceBackendRun = path.relative(repoRoot(), backendReportPath);
  const cases = selectedCases.map((caseConfig) =>
    buildCaseReport(caseConfig, backendRows.get(caseConfig.id), {
      sourceBackendRun,
    }),
  );
  const softCheckSummary = summarizeSoftChecks(cases);
  const renderedSuccessfully = cases.filter(
    (entry) => entry.render_status === "rendered",
  ).length;
  const renderFailures = cases.filter(
    (entry) => entry.render_status === "render_failed",
  ).length;
  const missingBackendRecords = cases.filter(
    (entry) => entry.render_status === "missing_backend_record",
  ).length;

  return {
    run_id: runId,
    generated_at: generatedAt,
    corpus_path: path.relative(repoRoot(), corpusPath),
    source_backend_run: sourceBackendRun,
    selected_case_count: selectedCases.length,
    rendered_successfully: renderedSuccessfully,
    render_failures: renderFailures,
    missing_backend_records: missingBackendRecords,
    soft_check_summary: softCheckSummary,
    cases_needing_manual_review: cases.map((entry) => entry.case_id),
    cases,
  };
}

export function writeFrontendCopyReport(
  report: FrontendCopyReport,
): FrontendCopyReportPaths {
  const outputDir = path.join(
    repoRoot(),
    "outputs",
    "frontend_copy_qa",
    report.run_id,
  );
  fs.mkdirSync(outputDir, { recursive: true });
  const jsonlPath = path.join(outputDir, "frontend_copy_report.jsonl");
  const markdownPath = path.join(outputDir, "frontend_copy_report.md");
  const summaryPath = path.join(outputDir, "summary.json");

  fs.writeFileSync(
    jsonlPath,
    `${report.cases.map((entry) => JSON.stringify(entry)).join("\n")}\n`,
  );
  fs.writeFileSync(markdownPath, formatMarkdownReport(report));
  fs.writeFileSync(
    summaryPath,
    `${JSON.stringify(
      {
        run_id: report.run_id,
        generated_at: report.generated_at,
        corpus_path: report.corpus_path,
        source_backend_run: report.source_backend_run,
        selected_case_count: report.selected_case_count,
        rendered_successfully: report.rendered_successfully,
        render_failures: report.render_failures,
        missing_backend_records: report.missing_backend_records,
        soft_check_summary: report.soft_check_summary,
        cases_needing_manual_review: report.cases_needing_manual_review,
      },
      null,
      2,
    )}\n`,
  );

  return {
    output_dir: outputDir,
    jsonl_path: jsonlPath,
    markdown_path: markdownPath,
    summary_path: summaryPath,
  };
}

export function formatMarkdownReport(report: FrontendCopyReport): string {
  const lines: string[] = [
    "# Frontend Copy QA Report",
    "",
    "## Summary",
    `- Run ID: ${report.run_id}`,
    `- Source backend run: ${report.source_backend_run}`,
    `- Selected cases: ${report.selected_case_count}`,
    `- Rendered successfully: ${report.rendered_successfully}`,
    `- Render failures: ${report.render_failures}`,
    `- Missing backend records: ${report.missing_backend_records}`,
    `- Soft check pass/fail/not checked: ${report.soft_check_summary.pass}/${report.soft_check_summary.fail}/${report.soft_check_summary.not_checked}`,
    `- Cases needing manual review: ${report.cases_needing_manual_review.length}`,
    "",
    "## Cases by category",
    "",
  ];

  const casesByCategory = new Map<string, FrontendCopyCaseReport[]>();
  for (const entry of report.cases) {
    const bucket = casesByCategory.get(entry.category) ?? [];
    bucket.push(entry);
    casesByCategory.set(entry.category, bucket);
  }

  for (const [category, entries] of casesByCategory) {
    lines.push(`## ${category}`, "");
    for (const entry of entries) {
      lines.push(...formatCaseMarkdown(entry), "");
    }
  }

  return `${lines.join("\n")}\n`;
}

function buildCaseReport(
  caseConfig: FrontendCopyCaseConfig,
  backendRecord: BackendQaRecord | undefined,
  options: { sourceBackendRun: string },
): FrontendCopyCaseReport {
  if (!backendRecord) {
    return baseCaseReport(caseConfig, options.sourceBackendRun, {
      renderStatus: "missing_backend_record",
      renderError: `No backend QA report row found for ${caseConfig.id}`,
      frontend: null,
      backendRecord: null,
    });
  }

  try {
    const response = rehydrateQueryResponse(backendRecord);
    const shape = classifyResultShape(response);
    const rendered = render(
      <article data-copy-region="case">
        <div data-copy-region="envelope">
          <ResultEnvelope data={response} />
        </div>
        <div data-copy-region="result">
          <ResultRenderer data={response} displayMode="review" />
        </div>
      </article>,
    );
    try {
      const frontend = extractFrontendCopy(rendered.container, shape);
      const softChecks = runSoftChecks(caseConfig, frontend);
      return {
        ...baseCaseReport(caseConfig, options.sourceBackendRun, {
          renderStatus: "rendered",
          renderError: null,
          frontend,
          backendRecord,
        }),
        soft_checks: softChecks,
        soft_check_summary: summarizeCaseSoftChecks(softChecks),
      };
    } finally {
      rendered.unmount();
    }
  } catch (error) {
    return baseCaseReport(caseConfig, options.sourceBackendRun, {
      renderStatus: "render_failed",
      renderError: error instanceof Error ? error.message : String(error),
      frontend: null,
      backendRecord,
    });
  }
}

function baseCaseReport(
  caseConfig: FrontendCopyCaseConfig,
  sourceBackendRun: string,
  options: {
    renderStatus: FrontendCopyCaseReport["render_status"];
    renderError: string | null;
    frontend: ExtractedFrontendCopy | null;
    backendRecord: BackendQaRecord | null;
  },
): FrontendCopyCaseReport {
  const backend = options.backendRecord;
  const softChecks = options.frontend
    ? runSoftChecks(caseConfig, options.frontend)
    : [];

  return {
    case_id: caseConfig.id,
    category: caseConfig.category,
    review_focus: caseConfig.review_focus,
    source_backend_run: sourceBackendRun,
    backend: {
      query: stringOrNull(backend?.query),
      route: stringOrNull(backend?.route),
      status: stringOrNull(backend?.result_status),
      reason: stringOrNull(backend?.result_reason),
      shape_hint: stringOrNull(backend?.shape_hint),
      shape_source: stringOrNull(backend?.shape_source),
      query_class: stringOrNull(backend?.query_class),
      sections: Object.keys(backend?.sections ?? {}),
      answer_text_policy: stringOrNull(backend?.answer_text_policy),
      manual_review_status: stringOrNull(backend?.manual_review?.status),
      manual_review_tags: stringArray(backend?.manual_review?.tags),
      informational_flags: stringArray(backend?.informational_flags),
      suspicious_flags: stringArray(backend?.suspicious_flags),
      verified_outliers: stringArray(backend?.verified_outliers),
    },
    render_status: options.renderStatus,
    render_error: options.renderError,
    frontend: options.frontend,
    soft_checks: softChecks,
    soft_check_summary: summarizeCaseSoftChecks(softChecks),
    review_status: "unreviewed",
    review_flags: [],
    review_notes: "",
  };
}

function rehydrateQueryResponse(record: BackendQaRecord): QueryResponse {
  const metadata = {
    ...(isObject(record.metadata) ? record.metadata : {}),
  };
  if (
    !Array.isArray(metadata.applied_filters) &&
    Array.isArray(record.applied_filters)
  ) {
    metadata.applied_filters = record.applied_filters;
  }

  const route = stringOrNull(record.route) ?? stringOrNull(metadata.route);
  const status = resultStatus(record.result_status);
  const notes = stringArray(record.notes);
  const caveats = stringArray(record.caveats);
  const currentThrough = stringOrNull(metadata.current_through);
  const queryClass =
    stringOrNull(record.query_class) ??
    stringOrNull(metadata.query_class) ??
    "summary";

  return {
    ok: Boolean(record.ok),
    query: stringOrNull(record.query) ?? "",
    route,
    result_status: status,
    result_reason: stringOrNull(record.result_reason),
    current_through: currentThrough,
    confidence: numberOrNull(metadata.confidence),
    intent: stringOrNull(record.intent) ?? stringOrNull(metadata.intent),
    alternates: [],
    notes,
    caveats,
    result: {
      query_class: queryClass,
      result_status: status,
      result_reason: stringOrNull(record.result_reason),
      current_through: currentThrough,
      metadata,
      notes,
      caveats,
      sections: record.sections ?? {},
    },
  };
}

function extractFrontendCopy(
  container: HTMLElement,
  shape: ReturnType<typeof classifyResultShape>,
): ExtractedFrontendCopy {
  const envelope = container.querySelector(
    '[data-copy-region="envelope"]',
  ) as HTMLElement | null;
  const result = container.querySelector(
    '[data-copy-region="result"]',
  ) as HTMLElement | null;

  if (!envelope || !result) {
    throw new Error("Rendered copy regions were not found");
  }

  const paragraphs = textList(result, "p, [class*='message']");
  const noResult = shape.key.startsWith("no_result")
    ? extractNoResultCopy(result)
    : null;
  const tables = Array.from(result.querySelectorAll("table")).map(
    (table, index) => extractTableCopy(table, index),
  );
  const envelopeBadges = Array.from(envelope.querySelectorAll("span"))
    .filter((element) => classText(element).includes("badge"))
    .map(spacedElementText)
    .filter(Boolean);
  const contextChips = Array.from(envelope.querySelectorAll("span"))
    .filter((element) => classText(element).includes("contextChip"))
    .map(spacedElementText)
    .filter(Boolean);
  const appliedFilterChips = Array.from(envelope.querySelectorAll("span"))
    .filter((element) => {
      const classes = classText(element);
      return classes.includes("contextChip") && classes.includes("accent");
    })
    .map(spacedElementText)
    .filter(Boolean);
  const resultHeadings = uniqueTexts([
    ...textList(result, "h1, h2, h3, h4, h5, h6"),
    ...textList(result, "[class*='sectionTitle']"),
  ]);
  const notesCaveatsRendered = uniqueTexts([
    ...textList(envelope, "li"),
    ...textList(result, '[aria-label="Result details"] [class*="detailItem"]'),
  ]);

  return {
    result_shape_key: shape.key,
    result_shape_name: shape.name,
    fallback_pattern: shape.key === "fallback_table",
    full_text: normalizeText(container.textContent),
    hero_text: noResult ? null : paragraphs[0] ?? null,
    supporting_text: noResult ? [] : uniqueTexts(paragraphs.slice(1, 6)),
    envelope_badges: uniqueTexts(envelopeBadges),
    context_chips: uniqueTexts(contextChips),
    applied_filter_chips: uniqueTexts(appliedFilterChips),
    envelope_context_items: uniqueTexts(textList(envelope, "li")),
    result_headings: resultHeadings,
    tables,
    no_result: noResult,
    notes_caveats_rendered: notesCaveatsRendered,
  };
}

function extractTableCopy(table: HTMLTableElement, index: number) {
  const firstRow = table.querySelector("tbody tr");
  return {
    index,
    aria_label: table.getAttribute("aria-label"),
    headers: textList(table, "thead th"),
    first_row: firstRow
      ? textList(firstRow, "th, td")
          .slice(0, 8)
          .map((text) => truncateText(text, 120))
      : [],
  };
}

function extractNoResultCopy(result: HTMLElement): ExtractedNoResultCopy {
  const titleCandidates = Array.from(
    result.querySelectorAll<HTMLElement>('[class*="title"]'),
  )
    .filter((element) => element.children.length === 0)
    .map((element) => normalizeText(element.textContent))
    .filter(Boolean);
  return {
    title: titleCandidates[0] ?? null,
    message:
      normalizeText(
        result.querySelector('[class*="message"]')?.textContent,
      ) || null,
    details: textList(
      result,
      '[aria-label="Result details"] [class*="detailItem"]',
    ),
    suggested_queries: textList(result, '[aria-label="Suggested queries"] code'),
    next_steps: textList(
      result,
      '[aria-label="Suggested next steps"] [class*="suggestion"]',
    ).filter((text) => text !== "Suggested next steps"),
  };
}

function runSoftChecks(
  caseConfig: FrontendCopyCaseConfig,
  frontend: ExtractedFrontendCopy,
): SoftCheckResult[] {
  const visibleText = compareText(frontend.full_text);
  const tableHeaders = compareText(
    frontend.tables
      .flatMap((table) => [table.aria_label ?? "", ...table.headers])
      .join(" "),
  );
  const filterChips = compareText(
    [
      ...frontend.applied_filter_chips,
      ...frontend.context_chips,
      ...frontend.envelope_context_items,
    ].join(" "),
  );
  const checks: SoftCheckResult[] = [];

  for (const fragment of caseConfig.expected_semantic_facts) {
    checks.push({
      kind: "semantic_fact",
      fragment,
      status: includesFragment(visibleText, fragment) ? "pass" : "fail",
      haystack: "visible_text",
    });
  }

  for (const fragment of caseConfig.expected_table_header_fragments) {
    checks.push({
      kind: "table_header_fragment",
      fragment,
      status: includesFragment(tableHeaders, fragment) ? "pass" : "fail",
      haystack: "table_headers",
    });
  }

  for (const fragment of caseConfig.expected_filter_chip_fragments) {
    checks.push({
      kind: "filter_chip_fragment",
      fragment,
      status: includesFragment(filterChips, fragment) ? "pass" : "fail",
      haystack: "filter_chips",
    });
  }

  for (const fragment of caseConfig.expected_absent_fragments) {
    checks.push({
      kind: "absent_fragment",
      fragment,
      status: includesFragment(visibleText, fragment) ? "fail" : "pass",
      haystack: "visible_text",
    });
  }

  if (checks.length === 0) {
    checks.push({
      kind: "semantic_fact",
      fragment: "",
      status: "not_checked",
      haystack: "visible_text",
    });
  }

  return checks;
}

function summarizeSoftChecks(cases: FrontendCopyCaseReport[]) {
  return cases.reduce(
    (summary, entry) => {
      summary.pass += entry.soft_check_summary.pass;
      summary.fail += entry.soft_check_summary.fail;
      summary.not_checked += entry.soft_check_summary.not_checked;
      return summary;
    },
    { pass: 0, fail: 0, not_checked: 0 },
  );
}

function summarizeCaseSoftChecks(checks: SoftCheckResult[]) {
  return checks.reduce(
    (summary, entry) => {
      summary[entry.status] += 1;
      return summary;
    },
    { pass: 0, fail: 0, not_checked: 0 },
  );
}

function formatCaseMarkdown(entry: FrontendCopyCaseReport): string[] {
  const frontend = entry.frontend;
  return [
    `### ${entry.case_id}`,
    `- Query: ${entry.backend.query ?? "unknown"}`,
    `- Backend: ${entry.backend.route ?? "none"} / ${entry.backend.status ?? "unknown"} / ${entry.backend.reason ?? "none"}`,
    `- Shape/pattern: ${frontend?.result_shape_name ?? entry.backend.shape_hint ?? "not rendered"}`,
    `- Render status: ${entry.render_status}${entry.render_error ? ` (${entry.render_error})` : ""}`,
    `- Hero: ${frontend?.hero_text ?? "none"}`,
    `- Supporting/context: ${formatList(frontend?.supporting_text ?? [])}`,
    `- Applied filters: ${formatList(frontend?.applied_filter_chips ?? [])}`,
    `- Result headings: ${formatList(frontend?.result_headings ?? [])}`,
    `- Table headers: ${formatTables(frontend?.tables ?? [])}`,
    `- Top row: ${formatTopRows(frontend?.tables ?? [])}`,
    `- No-result guidance: ${formatNoResult(frontend?.no_result ?? null)}`,
    `- Soft checks: ${entry.soft_check_summary.pass} pass, ${entry.soft_check_summary.fail} fail, ${entry.soft_check_summary.not_checked} not checked`,
    ...entry.soft_checks.map(
      (check) =>
        `  - ${check.status}: ${check.kind} ${check.fragment ? `"${check.fragment}"` : "(no fragment)"}`,
    ),
    `- Review status: ${entry.review_status}`,
    `- Notes: ${entry.review_notes || "none"}`,
  ];
}

function formatTables(tables: ExtractedTableCopy[]): string {
  if (tables.length === 0) return "none";
  return tables
    .map((table) => {
      const label = table.aria_label ? `${table.aria_label}: ` : "";
      return `${label}${table.headers.join(", ") || "no headers"}`;
    })
    .join(" | ");
}

function formatTopRows(tables: ExtractedTableCopy[]): string {
  const rows = tables
    .map((table) => table.first_row.join(" | "))
    .filter(Boolean);
  return formatList(rows);
}

function formatNoResult(noResult: ExtractedNoResultCopy | null): string {
  if (!noResult) return "none";
  return [
    noResult.title ? `title=${noResult.title}` : null,
    noResult.message ? `message=${noResult.message}` : null,
    noResult.details.length > 0
      ? `details=${noResult.details.join(" | ")}`
      : null,
    noResult.suggested_queries.length > 0
      ? `queries=${noResult.suggested_queries.join(" | ")}`
      : null,
    noResult.next_steps.length > 0
      ? `next=${noResult.next_steps.join(" | ")}`
      : null,
  ]
    .filter(Boolean)
    .join("; ");
}

function formatList(values: string[]): string {
  return values.length > 0 ? values.join(" | ") : "none";
}

function textList(root: ParentNode, selector: string): string[] {
  return uniqueTexts(
    Array.from(root.querySelectorAll(selector))
      .map((element) => normalizeText(element.textContent))
      .filter(Boolean),
  );
}

function parseYamlScalar(value: string | undefined): string {
  const trimmed = (value ?? "").trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function duplicateValues(values: string[]): string[] {
  const seen = new Set<string>();
  const duplicates = new Set<string>();
  for (const value of values) {
    if (seen.has(value)) {
      duplicates.add(value);
    }
    seen.add(value);
  }
  return [...duplicates];
}

function resultStatus(value: unknown): ResultStatus {
  if (value === "ok" || value === "no_result" || value === "error") {
    return value;
  }
  return "error";
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is string => typeof entry === "string");
}

function stringOrNull(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function classText(element: Element): string {
  const className = (element as HTMLElement).className;
  return typeof className === "string" ? className : "";
}

function normalizeText(value: unknown): string {
  if (typeof value !== "string") return "";
  return value.replace(/\s+/g, " ").trim();
}

function compareText(value: string): string {
  return normalizeText(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[–—]/g, "-")
    .replace(/[“”]/g, '"')
    .replace(/[‘’]/g, "'");
}

function includesFragment(haystack: string, fragment: string): boolean {
  return haystack.includes(compareText(fragment));
}

function uniqueTexts(values: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const value of values) {
    const normalized = normalizeText(value);
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    result.push(normalized);
  }
  return result;
}

function truncateText(value: string, maxLength: number): string {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1)}...`;
}

function spacedElementText(element: Element): string {
  return normalizeText(
    Array.from(element.childNodes)
      .map((node) => node.textContent ?? "")
      .join(" "),
  );
}

function createRunId(date = new Date()): string {
  return date
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\.\d{3}Z$/, "Z");
}
