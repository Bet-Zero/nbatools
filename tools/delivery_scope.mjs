// Narrow delivery selection, not a dependency graph. Unknown inputs run/build.
// Keep this list aligned with the reviewed build inputs in deployment.md.
import { execFileSync } from "node:child_process";
import { appendFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const PLANNING_DOCUMENTS = new Set([
  "AGENTS.md",
  "ROADMAP.md",
  "working/nba-tools-completion-program/README.md",
]);

function nonBuildInput(path) {
  return (
    PLANNING_DOCUMENTS.has(path) ||
    path.startsWith("tests/") ||
    path.startsWith("working/") ||
    path === "frontend/tools/captureCoreIdentityFindCount.mjs"
  );
}

export function classify(changes) {
  // Executable documents, symlinks, submodules and malformed records are unknown.
  const ordinary =
    changes.length > 0 &&
    changes.every(
      ({ path, oldMode, newMode }) =>
        typeof path === "string" &&
        !path.split("/").some((part) => ["", ".", ".."].includes(part)) &&
        ["000000", "100644"].includes(oldMode) &&
        ["000000", "100644"].includes(newMode),
    );
  return {
    application: !ordinary || !changes.every(({ path }) => PLANNING_DOCUMENTS.has(path)),
    deploy: !ordinary || !changes.every(({ path }) => nonBuildInput(path)),
  };
}

export function changedInputs(base, head, cwd = process.cwd()) {
  if (![base, head].every((sha) => typeof sha === "string" && /^[a-f0-9]{40}$/i.test(sha))) {
    throw new Error("missing or invalid comparison SHA");
  }
  // No HEAD^ fallback: a docs commit after an unbuilt runtime change must build.
  const git = (args) => execFileSync("git", args, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  git(["cat-file", "-e", `${head}^{commit}`]);
  git(["cat-file", "-e", `${base}^{commit}`]);
  git(["merge-base", "--is-ancestor", base, head]);
  const records = git(["diff", "--raw", "--no-ext-diff", "--no-renames", "-z", base, head]).split("\0");
  if (records.pop() !== "" || records.length % 2) throw new Error("invalid Git diff");
  const changes = [];
  for (let index = 0; index < records.length; index += 2) {
    const match = /^:(\d{6}) (\d{6}) [a-f0-9]+ [a-f0-9]+ [AMDT]$/.exec(records[index]);
    if (!match) throw new Error("unrecognized Git change");
    changes.push({ path: records[index + 1], oldMode: match[1], newMode: match[2] });
  }
  return changes;
}

export function select(base, head, cwd) {
  try {
    const changes = changedInputs(base, head, cwd);
    return { ...classify(changes), reason: "compared complete candidate range", paths: changes.map(({ path }) => path) };
  } catch {
    return { application: true, deploy: true, reason: "comparison unavailable or ambiguous; conservative validation/build", paths: [] };
  }
}

export function main(mode, env = process.env) {
  if (mode === "vercel") {
    if (env.NBATOOLS_FORCE_BUILD === "1") {
      console.log(JSON.stringify({ deploy: true, action: "build", reason: "explicit forced build" }));
      return 1;
    }
    const decision = select(env.VERCEL_GIT_PREVIOUS_SHA, env.VERCEL_GIT_COMMIT_SHA);
    console.log(JSON.stringify({ ...decision, action: decision.deploy ? "build" : "ignore unchanged application" }));
    // Vercel's documented protocol: 0 ignores, 1 continues the build.
    return decision.deploy ? 1 : 0;
  }
  if (mode !== "ci") throw new Error("expected ci or vercel mode");
  const event = env.GITHUB_EVENT_NAME;
  const decision = ["pull_request", "push"].includes(event)
    ? select(env.SCOPE_BASE_SHA, env.SCOPE_HEAD_SHA)
    : { application: true, deploy: true, reason: "full scheduled/manual/unknown-event backstop", paths: [] };
  console.log(JSON.stringify(decision));
  if (env.GITHUB_OUTPUT) appendFileSync(env.GITHUB_OUTPUT, `application=${decision.application}\n`);
  if (env.GITHUB_STEP_SUMMARY) {
    appendFileSync(env.GITHUB_STEP_SUMMARY,
      `Application checks: **${decision.application ? "selected" : "not selected"}**. ${decision.reason}.\n\n` +
      "Only the three reviewed planning documents qualify for the reduced path. Governance, policy, lint and both security verdicts still run. Unselected checks are not executed acceptance.\n");
  }
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = main(process.argv[2]);
}
