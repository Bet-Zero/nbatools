from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from nbatools.cli import app

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_RUNBOOK = "docs/operations/pipeline_runbook.md"
QUERY_GUIDE = "docs/reference/query_guide.md"
README = "README.md"


@dataclass(frozen=True)
class DocumentedCommand:
    doc_path: str
    command_text: str
    args: tuple[str, ...]


DOCUMENTED_COMMANDS = (
    DocumentedCommand(
        PIPELINE_RUNBOOK,
        "nbatools-cli ops backfill-season",
        ("ops", "backfill-season"),
    ),
    DocumentedCommand(
        PIPELINE_RUNBOOK,
        "nbatools-cli ops backfill-range",
        ("ops", "backfill-range"),
    ),
    DocumentedCommand(PIPELINE_RUNBOOK, "nbatools-cli ops inventory", ("ops", "inventory")),
    DocumentedCommand(
        PIPELINE_RUNBOOK,
        "nbatools-cli ops show-manifest",
        ("ops", "show-manifest"),
    ),
    DocumentedCommand(
        PIPELINE_RUNBOOK,
        "nbatools-cli ops update-manifest",
        ("ops", "update-manifest"),
    ),
    DocumentedCommand(
        PIPELINE_RUNBOOK,
        "nbatools-cli processing validate-raw",
        ("processing", "validate-raw"),
    ),
    DocumentedCommand(
        PIPELINE_RUNBOOK,
        "nbatools-cli pipeline refresh",
        ("pipeline", "refresh"),
    ),
    DocumentedCommand(
        PIPELINE_RUNBOOK,
        "nbatools-cli pipeline status",
        ("pipeline", "status"),
    ),
    DocumentedCommand(
        PIPELINE_RUNBOOK,
        "nbatools-cli pipeline publish-generation",
        ("pipeline", "publish-generation"),
    ),
    DocumentedCommand(
        PIPELINE_RUNBOOK,
        "nbatools-cli pipeline rollback-generation",
        ("pipeline", "rollback-generation"),
    ),
    DocumentedCommand(
        PIPELINE_RUNBOOK,
        "nbatools-cli pipeline recovery-drill",
        ("pipeline", "recovery-drill"),
    ),
    DocumentedCommand(README, "nbatools-cli ask", ("ask",)),
    DocumentedCommand(README, "nbatools-cli query routes", ("query", "routes")),
    DocumentedCommand(
        README,
        "nbatools-cli query route-help",
        ("query", "route-help"),
    ),
    DocumentedCommand(README, "nbatools-cli query route", ("query", "route")),
    *(
        DocumentedCommand(
            QUERY_GUIDE,
            f"nbatools-cli query {command}",
            ("query", command),
        )
        for command in (
            "top-player-games",
            "top-team-games",
            "season-leaders",
            "season-team-leaders",
            "player-game-finder",
            "game-finder",
            "player-game-summary",
            "game-summary",
            "player-compare",
            "team-compare",
        )
    ),
)


@pytest.mark.parametrize(
    "case",
    DOCUMENTED_COMMANDS,
    ids=lambda case: "-".join(case.args),
)
def test_documented_cli_command_path_has_working_help(case: DocumentedCommand) -> None:
    documentation = (ROOT / case.doc_path).read_text(encoding="utf-8")
    assert case.command_text in documentation

    result = CliRunner().invoke(app, [*case.args, "--help"])

    assert result.exit_code == 0, (
        f"{case.command_text} is documented but its --help path failed:\n"
        f"{result.output}\n{result.exception!r}"
    )


INLINE_CODE = re.compile(r"`([^`\n]+)`")
FULL_FRONTEND_PATH = re.compile(r"frontend/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+/?")


def _current_durable_docs() -> list[Path]:
    return [
        ROOT / README,
        *sorted((ROOT / "docs/architecture").rglob("*.md")),
        *sorted((ROOT / "docs/operations").rglob("*.md")),
        *sorted((ROOT / "docs/reference").rglob("*.md")),
    ]


def _documented_frontend_paths() -> dict[str, set[str]]:
    references: dict[str, set[str]] = {}
    for doc_path in _current_durable_docs():
        for token in INLINE_CODE.findall(doc_path.read_text(encoding="utf-8")):
            if not FULL_FRONTEND_PATH.fullmatch(token):
                continue
            relative_doc = str(doc_path.relative_to(ROOT))
            references.setdefault(token, set()).add(relative_doc)
    return references


def test_current_documented_frontend_paths_resolve_against_generated_layout() -> None:
    references = _documented_frontend_paths()
    assert references, "no exact frontend paths were found in current durable docs"

    inventory = json.loads(
        (ROOT / "contracts/repository_inventory.json").read_text(encoding="utf-8")
    )
    layout_root = inventory["frontend_layout"]["root"].rstrip("/")
    layout_files = set(inventory["frontend_layout"]["files"])

    failures: list[str] = []
    for relative_path, source_docs in sorted(references.items()):
        path = ROOT / relative_path
        sources = ", ".join(sorted(source_docs))
        if not path.exists():
            failures.append(f"{relative_path} does not exist (documented by {sources})")
            continue

        if relative_path == layout_root or relative_path.startswith(f"{layout_root}/"):
            if path.is_file() and relative_path not in layout_files:
                failures.append(f"{relative_path} is absent from generated frontend_layout")
            elif path.is_dir():
                prefix = f"{relative_path.rstrip('/')}/"
                if not any(item.startswith(prefix) for item in layout_files):
                    failures.append(f"{relative_path} has no files in generated frontend_layout")

    assert not failures, "\n".join(failures)


def test_frontend_visual_qa_json_and_yaml_are_semantically_equal() -> None:
    json_payload = json.loads(
        (ROOT / "qa/frontend_visual_qa_corpus.json").read_text(encoding="utf-8")
    )
    yaml_payload = yaml.safe_load(
        (ROOT / "qa/frontend_visual_qa_corpus.yaml").read_text(encoding="utf-8")
    )

    assert yaml_payload == json_payload
