import visualQaCorpusJson from "../../qa/frontend_visual_qa_corpus.json";

export type VisualQaViewport = "desktop_1280" | "mobile_390";

export interface VisualQaCase {
  id: string;
  category: string;
  query: string;
  viewports: VisualQaViewport[];
  visual_focus: string[];
  desktop_focus: string[];
  mobile_focus: string[];
  expected_primary_visual_concerns: string[];
}

interface VisualQaCorpus {
  version: number;
  provenance_raw_run: string;
  provenance_frontend_copy_run: string;
  cases: VisualQaCase[];
}

function parseVisualQaCorpus(parsed: unknown): VisualQaCorpus {
  const corpus = parsed as Partial<VisualQaCorpus>;

  if (!Array.isArray(corpus.cases)) {
    throw new Error("Visual QA corpus is missing its cases array.");
  }

  if (typeof corpus.provenance_raw_run !== "string") {
    throw new Error("Visual QA corpus is missing provenance_raw_run.");
  }

  if (typeof corpus.provenance_frontend_copy_run !== "string") {
    throw new Error(
      "Visual QA corpus is missing provenance_frontend_copy_run.",
    );
  }

  return {
    version: typeof corpus.version === "number" ? corpus.version : 1,
    provenance_raw_run: corpus.provenance_raw_run,
    provenance_frontend_copy_run: corpus.provenance_frontend_copy_run,
    cases: corpus.cases as VisualQaCase[],
  };
}

const visualQaCorpus = parseVisualQaCorpus(visualQaCorpusJson);

export const VISUAL_QA_INTERNAL_ROUTE = "/visual-qa";
export const VISUAL_QA_CHECKLIST_DOC =
  "docs/operations/frontend_visual_qa.md";
export const VISUAL_QA_PROVENANCE_RAW_RUN =
  visualQaCorpus.provenance_raw_run;
export const VISUAL_QA_PROVENANCE_FRONTEND_COPY_RUN =
  visualQaCorpus.provenance_frontend_copy_run;
export const VISUAL_QA_CASES = visualQaCorpus.cases;
