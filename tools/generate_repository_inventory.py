#!/usr/bin/env python3
"""Generate deterministic repository-surface inventory from authoritative sources.

This tool intentionally uses only the Python standard library. It parses the
small, explicit source declarations instead of importing application modules,
so the governance check remains runnable before project dependencies are
installed and never depends on ignored runtime data.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = Path("contracts/repository_inventory.json")

ROUTES_PATH = Path("src/nbatools/query_service.py")
RESULT_TYPES_PATH = Path("src/nbatools/commands/format_output.py")
RESULT_REASONS_PATH = Path("src/nbatools/commands/structured_results.py")
DATASET_SPECS_PATH = Path("src/nbatools/commands/validation_control.py")
RAW_QA_CORPUS_PATH = Path("qa/raw_query_answer_corpus.yaml")
ACCEPTANCE_FAMILIES_PATH = Path("qa/raw_query_answer_acceptance_families.yaml")
HARNESS_SLICES_PATH = Path("qa/harness_slices")
FRONTEND_ROUTE_TYPES_PATH = Path("frontend/src/api/types.ts")
FRONTEND_SOURCE_ROOT = Path("frontend/src")

DATASET_SPEC_FIELDS = (
    "name",
    "layer",
    "grain",
    "key_columns",
    "source",
    "required_columns",
    "required",
    "season_only",
    "regular_season_only",
    "trust_column",
    "trust_reason_column",
)
DATASET_SPEC_DEFAULTS: dict[str, Any] = {
    "required_columns": (),
    "required": True,
    "season_only": False,
    "regular_season_only": False,
    "trust_column": None,
    "trust_reason_column": None,
}
DATASET_INVENTORY_FIELDS = (
    "name",
    "layer",
    "grain",
    "key_columns",
    "source",
    "required",
    "season_only",
    "regular_season_only",
    "trust_column",
    "trust_reason_column",
)

IDENTIFIER = re.compile(r"[A-Za-z0-9_]+")
TYPESCRIPT_UNION_STRING_ITEM = re.compile(r'^\s*\|\s*"([A-Za-z0-9_]+)"(;)?$')
TYPESCRIPT_UNION_NULL_ITEM = re.compile(r"^\s*\|\s*null(;)?$")


class InventoryError(ValueError):
    """Raised when an authoritative source no longer matches its contract."""


def _read_ast(root: Path, path: Path) -> ast.Module:
    source_path = root / path
    try:
        return ast.parse(source_path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise InventoryError(f"cannot parse {path}: {exc}") from exc


def _assignment_value(tree: ast.Module, symbol: str, path: Path) -> ast.expr:
    matches: list[ast.expr] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == symbol for target in node.targets
        ):
            matches.append(node.value)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == symbol
            and node.value is not None
        ):
            matches.append(node.value)
    if len(matches) != 1:
        raise InventoryError(f"{path}: expected exactly one assignment to {symbol}")
    return matches[0]


def _unique_strings(values: Any, *, label: str) -> list[str]:
    if not isinstance(values, (list, tuple)) or not all(
        isinstance(value, str) and value for value in values
    ):
        raise InventoryError(f"{label}: expected a sequence of non-empty strings")
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        raise InventoryError(f"{label}: duplicate values: {', '.join(duplicates)}")
    return sorted(values)


def collect_structured_routes(root: Path) -> list[str]:
    tree = _read_ast(root, ROUTES_PATH)
    value = _assignment_value(tree, "VALID_ROUTES", ROUTES_PATH)
    if not (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "frozenset"
        and len(value.args) == 1
        and not value.keywords
    ):
        raise InventoryError(f"{ROUTES_PATH}: VALID_ROUTES must be frozenset(<literal sequence>)")
    try:
        routes = ast.literal_eval(value.args[0])
    except (ValueError, TypeError) as exc:
        raise InventoryError(f"{ROUTES_PATH}: VALID_ROUTES is not literal") from exc
    return _unique_strings(routes, label=f"{ROUTES_PATH}: VALID_ROUTES")


def _collect_frontend_string_union(
    root: Path,
    type_name: str,
    *,
    nullable: bool = False,
) -> list[str]:
    path = root / FRONTEND_ROUTE_TYPES_PATH
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise InventoryError(f"cannot read {FRONTEND_ROUTE_TYPES_PATH}: {exc}") from exc
    starts = [index for index, line in enumerate(lines) if line == f"export type {type_name} ="]
    if len(starts) != 1:
        raise InventoryError(f"{FRONTEND_ROUTE_TYPES_PATH}: expected exactly one {type_name} union")
    names: list[str] = []
    saw_null = False
    terminated = False
    for line_number, line in enumerate(lines[starts[0] + 1 :], start=starts[0] + 2):
        string_match = TYPESCRIPT_UNION_STRING_ITEM.fullmatch(line)
        null_match = TYPESCRIPT_UNION_NULL_ITEM.fullmatch(line)
        if string_match is not None:
            if saw_null:
                raise InventoryError(
                    f"{FRONTEND_ROUTE_TYPES_PATH}:{line_number}: "
                    f"{type_name} values cannot follow null"
                )
            names.append(string_match.group(1))
            is_terminated = bool(string_match.group(2))
        elif null_match is not None and nullable and not saw_null:
            saw_null = True
            is_terminated = bool(null_match.group(1))
        else:
            raise InventoryError(
                f"{FRONTEND_ROUTE_TYPES_PATH}:{line_number}: unexpected {type_name} union item"
            )
        if is_terminated:
            terminated = True
            break
    if not terminated:
        raise InventoryError(f"{FRONTEND_ROUTE_TYPES_PATH}: {type_name} union is not terminated")
    if nullable != saw_null:
        expected = "must" if nullable else "must not"
        raise InventoryError(
            f"{FRONTEND_ROUTE_TYPES_PATH}: {type_name} union {expected} include null"
        )
    return _unique_strings(names, label=f"{FRONTEND_ROUTE_TYPES_PATH}: {type_name}")


def collect_frontend_route_names(root: Path) -> list[str]:
    return _collect_frontend_string_union(root, "RouteName")


def collect_frontend_result_reasons(root: Path) -> list[str]:
    return _collect_frontend_string_union(root, "ResultReason", nullable=True)


def collect_frontend_layout(root: Path) -> list[str]:
    source_root = root / FRONTEND_SOURCE_ROOT
    files = sorted(
        str(path.relative_to(root))
        for path in source_root.rglob("*")
        if path.is_file() and not path.name.startswith(".")
    )
    if not files:
        raise InventoryError(f"{FRONTEND_SOURCE_ROOT}: no source files found")
    return files


def collect_result_reasons(root: Path) -> list[str]:
    tree = _read_ast(root, RESULT_REASONS_PATH)
    matches = [
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ResultReason"
    ]
    if len(matches) != 1:
        raise InventoryError(f"{RESULT_REASONS_PATH}: expected exactly one ResultReason enum")
    values: list[str] = []
    for node in matches[0].body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise InventoryError(
                f"{RESULT_REASONS_PATH}: ResultReason members must be simple assignments"
            )
        value = _literal(
            node.value,
            label=f"{RESULT_REASONS_PATH}: ResultReason.{node.targets[0].id}",
        )
        if not isinstance(value, str) or not value:
            raise InventoryError(
                f"{RESULT_REASONS_PATH}: ResultReason values must be non-empty strings"
            )
        values.append(value)
    if not values:
        raise InventoryError(f"{RESULT_REASONS_PATH}: ResultReason has no members")
    return _unique_strings(values, label=f"{RESULT_REASONS_PATH}: ResultReason")


def _flatten_union_names(value: ast.expr, *, path: Path) -> list[str]:
    if isinstance(value, ast.Name):
        return [value.id]
    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.BitOr):
        return [
            *_flatten_union_names(value.left, path=path),
            *_flatten_union_names(value.right, path=path),
        ]
    raise InventoryError(f"{path}: StructuredResult must be a union of simple class names")


def collect_structured_result_types(root: Path) -> list[str]:
    tree = _read_ast(root, RESULT_TYPES_PATH)
    value = _assignment_value(tree, "StructuredResult", RESULT_TYPES_PATH)
    return _unique_strings(
        _flatten_union_names(value, path=RESULT_TYPES_PATH),
        label=f"{RESULT_TYPES_PATH}: StructuredResult",
    )


def _dataset_spec_class_fields(tree: ast.Module) -> tuple[str, ...]:
    matches = [
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "DatasetSpec"
    ]
    if len(matches) != 1:
        raise InventoryError(f"{DATASET_SPECS_PATH}: expected exactly one DatasetSpec class")
    declarations = [
        node
        for node in matches[0].body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ]
    fields = tuple(node.target.id for node in declarations)
    if fields != DATASET_SPEC_FIELDS:
        raise InventoryError(
            f"{DATASET_SPECS_PATH}: DatasetSpec fields changed; update inventory parser"
        )
    defaults = {
        node.target.id: _literal(
            node.value,
            label=f"{DATASET_SPECS_PATH}: DatasetSpec default {node.target.id}",
        )
        for node in declarations
        if node.value is not None
    }
    if defaults != DATASET_SPEC_DEFAULTS:
        raise InventoryError(
            f"{DATASET_SPECS_PATH}: DatasetSpec defaults changed; update inventory parser"
        )
    return fields


def _literal(node: ast.expr, *, label: str) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError) as exc:
        raise InventoryError(f"{label}: expected a literal value") from exc


def _dataset_spec_item(node: ast.expr, *, index: int) -> dict[str, Any]:
    label = f"{DATASET_SPECS_PATH}: DATASET_SPECS item {index}"
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "DatasetSpec"
    ):
        raise InventoryError(f"{label}: expected a DatasetSpec(...) call")
    if len(node.args) > len(DATASET_SPEC_FIELDS):
        raise InventoryError(f"{label}: too many positional arguments")

    values: dict[str, Any] = dict(DATASET_SPEC_DEFAULTS)
    assigned: set[str] = set()
    for field, argument in zip(DATASET_SPEC_FIELDS, node.args, strict=False):
        assigned.add(field)
        if field != "required_columns":
            values[field] = _literal(argument, label=f"{label} {field}")

    for keyword in node.keywords:
        if keyword.arg is None or keyword.arg not in DATASET_SPEC_FIELDS:
            raise InventoryError(f"{label}: unexpected keyword argument")
        if keyword.arg in assigned:
            raise InventoryError(f"{label}: duplicate argument {keyword.arg}")
        assigned.add(keyword.arg)
        if keyword.arg != "required_columns":
            values[keyword.arg] = _literal(
                keyword.value,
                label=f"{label} {keyword.arg}",
            )

    missing = [field for field in DATASET_SPEC_FIELDS[:5] if field not in assigned]
    if missing:
        raise InventoryError(f"{label}: missing required arguments: {', '.join(missing)}")

    for field in ("name", "layer", "grain", "source"):
        if not isinstance(values[field], str) or not values[field]:
            raise InventoryError(f"{label} {field}: expected a non-empty string")
    key_columns = values["key_columns"]
    if (
        not isinstance(key_columns, (list, tuple))
        or not key_columns
        or not all(isinstance(column, str) and column for column in key_columns)
    ):
        raise InventoryError(f"{label} key_columns: expected non-empty string sequence")
    values["key_columns"] = list(key_columns)
    for field in ("required", "season_only", "regular_season_only"):
        if not isinstance(values[field], bool):
            raise InventoryError(f"{label} {field}: expected a boolean")
    for field in ("trust_column", "trust_reason_column"):
        if values[field] is not None and (not isinstance(values[field], str) or not values[field]):
            raise InventoryError(f"{label} {field}: expected null or non-empty string")

    return {field: values[field] for field in DATASET_INVENTORY_FIELDS}


def collect_dataset_specs(root: Path) -> list[dict[str, Any]]:
    tree = _read_ast(root, DATASET_SPECS_PATH)
    _dataset_spec_class_fields(tree)
    value = _assignment_value(tree, "DATASET_SPECS", DATASET_SPECS_PATH)
    if not isinstance(value, (ast.Tuple, ast.List)):
        raise InventoryError(f"{DATASET_SPECS_PATH}: DATASET_SPECS must be a sequence")
    items = [
        _dataset_spec_item(node, index=index) for index, node in enumerate(value.elts, start=1)
    ]
    names = [item["name"] for item in items]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise InventoryError(
            f"{DATASET_SPECS_PATH}: duplicate dataset names: {', '.join(duplicates)}"
        )
    return sorted(items, key=lambda item: item["name"])


def _section_lines(path: Path, section: str) -> list[tuple[int, str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise InventoryError(f"cannot read {path}: {exc}") from exc
    starts = [index for index, line in enumerate(lines) if line == f"{section}:"]
    if len(starts) != 1:
        raise InventoryError(f"{path}: expected exactly one top-level {section}: section")
    selected: list[tuple[int, str]] = []
    for index in range(starts[0] + 1, len(lines)):
        line = lines[index]
        if line and not line[0].isspace() and not line.startswith("#"):
            break
        selected.append((index + 1, line))
    return selected


def _parse_identifier(raw: str, *, path: Path, line_number: int) -> str:
    value = raw.strip()
    if not IDENTIFIER.fullmatch(value):
        raise InventoryError(f"{path}:{line_number}: expected an unquoted identifier")
    return value


def _top_level_identifier(path: Path, key: str) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise InventoryError(f"cannot read {path}: {exc}") from exc
    prefix = f"{key}: "
    matches = [
        (line_number, line.removeprefix(prefix))
        for line_number, line in enumerate(lines, start=1)
        if line.startswith(prefix)
    ]
    if len(matches) != 1:
        raise InventoryError(f"{path}: expected exactly one top-level {key}: value")
    line_number, raw = matches[0]
    return _parse_identifier(raw, path=path, line_number=line_number)


def _mapping_sequence_ids(path: Path, section: str) -> list[str]:
    values: list[str] = []
    for line_number, line in _section_lines(path, section):
        if not line.startswith("  -"):
            continue
        if not line.startswith("  - id: "):
            raise InventoryError(f"{path}:{line_number}: expected '  - id: <identifier>'")
        values.append(
            _parse_identifier(
                line.removeprefix("  - id: "),
                path=path,
                line_number=line_number,
            )
        )
    if not values:
        raise InventoryError(f"{path}: {section} contains no items")
    return _unique_strings(values, label=f"{path}: {section}")


def _scalar_sequence_ids(path: Path, section: str) -> list[str]:
    values: list[str] = []
    for line_number, line in _section_lines(path, section):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith("  - "):
            raise InventoryError(f"{path}:{line_number}: expected '  - <identifier>'")
        values.append(
            _parse_identifier(
                line.removeprefix("  - "),
                path=path,
                line_number=line_number,
            )
        )
    if not values:
        raise InventoryError(f"{path}: {section} contains no items")
    return _unique_strings(values, label=f"{path}: {section}")


def collect_query_validation(root: Path) -> dict[str, Any]:
    corpus_path = root / RAW_QA_CORPUS_PATH
    family_path = root / ACCEPTANCE_FAMILIES_PATH
    case_ids = _mapping_sequence_ids(corpus_path, "cases")
    family_ids = _mapping_sequence_ids(family_path, "families")
    known_cases = set(case_ids)

    slices_dir = root / HARNESS_SLICES_PATH
    slice_paths = sorted(slices_dir.glob("*.yaml"))
    if not slice_paths:
        raise InventoryError(f"{HARNESS_SLICES_PATH}: no YAML slice files found")
    slice_case_counts: dict[str, int] = {}
    for path in slice_paths:
        relative_path = path.relative_to(root)
        slice_name = _top_level_identifier(path, "name")
        if slice_name != path.stem:
            raise InventoryError(
                f"{relative_path}: slice name {slice_name!r} must match filename stem {path.stem!r}"
            )
        slice_ids = _scalar_sequence_ids(path, "case_ids")
        unknown = sorted(set(slice_ids) - known_cases)
        if unknown:
            raise InventoryError(f"{relative_path}: unknown corpus case ids: {', '.join(unknown)}")
        if slice_name in slice_case_counts:
            raise InventoryError(f"{HARNESS_SLICES_PATH}: duplicate slice name {slice_name}")
        slice_case_counts[slice_name] = len(slice_ids)

    return {
        "acceptance_family_count": len(family_ids),
        "acceptance_family_ids": family_ids,
        "raw_qa_case_count": len(case_ids),
        "slice_case_counts": slice_case_counts,
    }


def build_inventory(root: Path = ROOT) -> dict[str, Any]:
    routes = collect_structured_routes(root)
    frontend_routes = collect_frontend_route_names(root)
    if frontend_routes != routes:
        backend = set(routes)
        frontend = set(frontend_routes)
        missing = ", ".join(sorted(backend - frontend)) or "none"
        extra = ", ".join(sorted(frontend - backend)) or "none"
        raise InventoryError(
            f"{FRONTEND_ROUTE_TYPES_PATH}: RouteName differs from VALID_ROUTES "
            f"(missing: {missing}; extra: {extra})"
        )
    result_reasons = collect_result_reasons(root)
    frontend_result_reasons = collect_frontend_result_reasons(root)
    if frontend_result_reasons != result_reasons:
        backend = set(result_reasons)
        frontend = set(frontend_result_reasons)
        missing = ", ".join(sorted(backend - frontend)) or "none"
        extra = ", ".join(sorted(frontend - backend)) or "none"
        raise InventoryError(
            f"{FRONTEND_ROUTE_TYPES_PATH}: ResultReason differs from backend enum "
            f"(missing: {missing}; extra: {extra})"
        )
    result_types = collect_structured_result_types(root)
    dataset_specs = collect_dataset_specs(root)
    frontend_layout = collect_frontend_layout(root)
    return {
        "dataset_specs": {
            "count": len(dataset_specs),
            "field_scope": list(DATASET_INVENTORY_FIELDS),
            "items": dataset_specs,
            "omitted_fields": ["required_columns"],
        },
        "frontend_layout": {
            "count": len(frontend_layout),
            "files": frontend_layout,
            "root": str(FRONTEND_SOURCE_ROOT),
        },
        "query_validation": collect_query_validation(root),
        "schema_version": 1,
        "sources": {
            "acceptance_families": str(ACCEPTANCE_FAMILIES_PATH),
            "dataset_specs": str(DATASET_SPECS_PATH),
            "frontend_route_names": str(FRONTEND_ROUTE_TYPES_PATH),
            "frontend_result_reasons": str(FRONTEND_ROUTE_TYPES_PATH),
            "frontend_layout": str(FRONTEND_SOURCE_ROOT),
            "raw_qa_corpus": str(RAW_QA_CORPUS_PATH),
            "result_reasons": str(RESULT_REASONS_PATH),
            "raw_qa_slices": f"{HARNESS_SLICES_PATH}/*.yaml",
            "structured_result_types": str(RESULT_TYPES_PATH),
            "structured_routes": str(ROUTES_PATH),
        },
        "structured_result_types": {
            "count": len(result_types),
            "names": result_types,
        },
        "result_reasons": {
            "count": len(result_reasons),
            "names": result_reasons,
        },
        "structured_routes": {
            "count": len(routes),
            "names": routes,
        },
    }


def render_inventory(inventory: dict[str, Any]) -> str:
    return json.dumps(inventory, indent=2, sort_keys=True) + "\n"


def write_inventory(root: Path = ROOT, output_path: Path | None = None) -> Path:
    target = output_path or root / OUTPUT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_inventory(build_inventory(root)), encoding="utf-8")
    return target


def check_inventory(root: Path = ROOT, output_path: Path | None = None) -> bool:
    target = output_path or root / OUTPUT_PATH
    expected = render_inventory(build_inventory(root))
    try:
        actual = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"repository inventory is missing: {target}")
        return False
    if actual == expected:
        print("repository inventory check passed")
        return True
    print("repository inventory is stale; run `make repository-inventory`")
    print(
        "".join(
            difflib.unified_diff(
                actual.splitlines(keepends=True),
                expected.splitlines(keepends=True),
                fromfile=str(target),
                tofile="generated repository inventory",
            )
        ),
        end="",
    )
    return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true", help="write the canonical inventory")
    action.add_argument("--check", action="store_true", help="fail if the inventory is stale")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.write:
            target = write_inventory()
            print(f"wrote {target.relative_to(ROOT)}")
            return 0
        return 0 if check_inventory() else 1
    except InventoryError as exc:
        print(f"repository inventory generation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
