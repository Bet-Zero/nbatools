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
  source_raw_run: string;
  source_frontend_copy_run: string;
  cases: VisualQaCase[];
}

function parseVisualQaCorpus(parsed: unknown): VisualQaCorpus {
  const corpus = parsed as Partial<VisualQaCorpus>;

  if (!Array.isArray(corpus.cases)) {
    throw new Error("Visual QA corpus is missing its cases array.");
  }

  if (typeof corpus.source_raw_run !== "string") {
    throw new Error("Visual QA corpus is missing source_raw_run.");
  }

  if (typeof corpus.source_frontend_copy_run !== "string") {
    throw new Error("Visual QA corpus is missing source_frontend_copy_run.");
  }

  return {
    version: typeof corpus.version === "number" ? corpus.version : 1,
    source_raw_run: corpus.source_raw_run,
    source_frontend_copy_run: corpus.source_frontend_copy_run,
    cases: corpus.cases as VisualQaCase[],
  };
}

const visualQaCorpus = parseVisualQaCorpus(visualQaCorpusJson);

export const VISUAL_QA_INTERNAL_ROUTE = "/visual-qa";
export const VISUAL_QA_CHECKLIST_DOC =
  "docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md";
export const VISUAL_QA_SOURCE_RAW_RUN = visualQaCorpus.source_raw_run;
export const VISUAL_QA_SOURCE_FRONTEND_COPY_RUN =
  visualQaCorpus.source_frontend_copy_run;
export const VISUAL_QA_CASES = visualQaCorpus.cases;
