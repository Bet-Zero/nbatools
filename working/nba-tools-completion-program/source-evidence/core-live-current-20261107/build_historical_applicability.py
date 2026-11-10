"""Reproduce the reviewed applicability companion; no NBA/public/data queries.

Run with Python from any directory. A reviewer must inspect every changed-file
semantic rule, then separately pin the generated SHA in the existing verifier.
This preserves the original binding, case/capture bytes and acceptance scope.
"""

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import ZipFile

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
EVIDENCE = Path(__file__).resolve().parent
OLD = "a0fb2211a6707d647325129f1262308545001241"
PARSER = "src/nbatools/commands/_parse_helpers.py"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


semantic = {
    "docs/reference/data_contracts.md": (
        "documentation",
        "No runtime execution; source definitions remain independently checked.",
    ),
    "src/nbatools/commands/_parse_helpers.py": (
        "opponent-list/period detection",
        (
            "All original 22 inputs have identical old/current regex matches; all "
            "quarter/half predicates are None, no vs/against either phrase."
        ),
    ),
    "src/nbatools/commands/_reported_absence_reasons.py": (
        "load_observations/source_entry",
        (
            "New explicit development lineage path requires selected_snapshot; original 22 "
            "historical queries have none and request no reported reason; published "
            "manifest path unchanged."
        ),
    ),
    "src/nbatools/commands/_natural_query_execution.py": (
        "_execute_grouped_boolean_build_result",
        (
            "New checked-finder delegation requires quarter or half in base_kwargs. Both "
            "predicates are None for all original 22 queries. The existing team/opponent "
            "leaf delegation, including the two owned whole-game cases, remains identical."
        ),
    ),
    "src/nbatools/commands/_matchup_utils.py": (
        "team/opponent scans; extract_team_comparison; presence clause punctuation",
        (
            "The original 22 names are Curry, Brunson, Jokic, Ewing, LeBron James, Tatum "
            "and Brown, none with internal team-alias words or initial periods. New "
            "full-person team masking therefore preserves their explicit team/opponent "
            "mentions. No original query uses PLAYER for TEAM versus OPPONENT. Presence "
            "name punctuation changes only initial periods, absent from these inputs."
        ),
    ),
    "src/nbatools/commands/aggregate_metrics.py": (
        "require_known_metric_inputs; fractional_source_rate_bounds",
        (
            "New helper returns before accessing data when selected_snapshot() is None; its"
            " new calls, including row-rate denominator checks, are also period-predicate gated."
            " The new fraction conversion helper is called only under the natural period flag."
        ),
    ),
    "src/nbatools/commands/data_utils.py": (
        "player-period loading/OT coverage",
        (
            "New direct loader/dependency path requires an explicit development selector; OT "
            "source-population specialization also requires both overtime request and "
            "selector. Zero-attempt TS/eFG null derivation requires a selected snapshot. "
            "None of the 22 queries requests periods."
        ),
    ),
    "src/nbatools/commands/entity_resolution.py": (
        "resolve_player_in_query; mask_player_owned_team_words; resolve_team_in_query",
        (
            "All original 22 person names lack internal team-alias words and initial "
            "periods. Their complete-name-before-alias precedence and identities remain "
            "unchanged. The new substring precheck is equivalent to the following bounded "
            "regex; broader full-name lookup adds no different matching person to these "
            "exact names. Team masking does not erase any independent team mention."
        ),
    ),
    "src/nbatools/commands/pipeline/player_game_availability_report.py": (
        "_split_inactives/_inactives",
        (
            "Selected-target reason acquisition/import helper, none of the original 22 "
            "historical queries executes source reimport or requests a reported reason."
        ),
    ),
    "src/nbatools/commands/pipeline/reported_absence_reasons.py": (
        "_observe",
        (
            "Selected-target source preparation, none of the original 22 historical queries "
            "executes source reimport."
        ),
    ),
    "src/nbatools/commands/player_game_finder.py": (
        "build_result",
        (
            "New selection/ranking checks, context/margin basis refusal, attempt eligibility, "
            "deferred filtering and undefined/source rate notes are "
            "period_filter_requested gated. All 22 have no period request. In the false "
            "branch, stat/conditions old initial filters and default empty metadata remain "
            "equivalent. New scalar/list/tree bound conversion additionally requires the "
            "natural source-rate flag and a quarter/half request, absent from all 22 queries."
        ),
    ),
    "src/nbatools/commands/natural_query.py": (
        "_finalize_route; _teams_in_order; _team_mentions",
        (
            "The new private natural source-rate unit flag requires player_game_finder plus "
            "a quarter or half. Original 22 queries have neither period predicate, so their "
            "route kwargs remain unchanged and no bound conversion is selected."
            " New team-mention masking only hides complete person spans with internal "
            "team words; none of the original 22 names contains one, so team lists and "
            "comparison subjects remain identical."
        ),
    ),
    "src/nbatools/commands/team_record.py": (
        "build_team_record_result caveat",
        "Changed caveat is period_execution_backed gated; all 22 have no period request.",
    ),
    "src/nbatools/commands/validation_control.py": (
        "apply_cross_dataset_coverage",
        (
            "Offline strict OT dataset coverage, not historical query arithmetic/rendering."
            " Full publication/readiness gate not claimed by replay."
        ),
    ),
    "src/nbatools/development_data.py": (
        "DevelopmentDataUnavailable/DevelopmentSnapshot",
        (
            "New dependency-qualified byte/hash/schema reader requires a selected "
            "development snapshot. Published original 22 historical queries have no such "
            "context; no production fallback."
        ),
    ),
    "src/nbatools/query_service.py": (
        "_build_query_metadata; _build_applied_filters; structured metadata call site",
        (
            "Numeric bound metadata conversion requires the private natural source-rate "
            "flag. That flag is set only for period player finders, absent from all 22 "
            "queries; original whole-game labels, values and numeric metadata are unchanged."
            " The additive Playing for label requires an actual primary player plus explicit "
            "team; none of these 22 player requests has a team filter and team requests have "
            "no primary player. The existing comparison rule remains the same. Passing real "
            "structured kwargs preserves this same ownership condition, without changing "
            "the original natural HTTP captures."
        ),
    ),
}


def main():
    binding_raw = (EVIDENCE / "live-code-binding.json").read_bytes()
    assert sha(binding_raw) == "b2c2e145acec65db5e7707cb69ae4d1a194c19b97f5a2a52e3dbe632e326638f"
    binding = json.loads(binding_raw)
    archive = EVIDENCE / "historical-live-original.zip"
    assert (
        sha(archive.read_bytes())
        == "a5c718c7498f24d787866ff4e3d53220363e00588a045607e92f5947ac2074a5"
    )
    with ZipFile(archive) as z:
        cases_raw = z.read("acquired_data/core-historical-live/cases.json")
        cases = [{"id": c["id"], "query": c["query"]} for c in json.loads(cases_raw)]
    assert len(cases) == 22 and len(binding["application_file_sha256"]) == 663
    changes = []
    for path, old_hash in binding["application_file_sha256"].items():
        actual = sha((ROOT / path).read_bytes())
        if actual == old_hash:
            continue
        assert path in semantic, ("Unreviewed changed bound file", path)
        functions, reach = semantic[path]
        changes.append(
            dict(
                path=path,
                old_sha256=old_hash,
                reviewed_sha256=actual,
                reviewed_functions=functions,
                semantic_reach=reach,
                eligible_existing_case_ids=[c["id"] for c in cases],
            )
        )
    assert set(c["path"] for c in changes) == set(semantic)
    old_parser = subprocess.check_output(["git", "show", OLD + ":" + PARSER], cwd=ROOT, text=True)
    assert sha(old_parser.encode()) == binding["application_file_sha256"][PARSER]
    tree = ast.parse(old_parser)
    nodes = [
        n
        for n in tree.body
        if (isinstance(n, ast.FunctionDef) and n.name in {"detect_quarter", "detect_half"})
        or (
            isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "_LIST_VS" for t in n.targets)
        )
    ]
    assert len(nodes) == 3
    predicates = "\n\n".join(ast.get_source_segment(old_parser, n) for n in nodes) + "\n"
    inventory = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", OLD, "src"], cwd=ROOT, text=True
    ).splitlines()
    inventory = sorted(p for p in inventory if p.endswith(".py"))
    assert inventory == sorted(str(p.relative_to(ROOT)) for p in (ROOT / "src").rglob("*.py"))
    proof = dict(
        classification="retained_original44_applicability_only",
        reviewer="/root/finite_core_acceptance_review",
        backend_model="unavailable",
        original_deployed_code=OLD,
        live_binding_sha256=sha(binding_raw),
        original_capture_sha256=sha(archive.read_bytes()),
        original_case_manifest_sha256=sha(cases_raw),
        original_bound_file_count=663,
        unchanged_bound_file_count=663 - len(changes),
        cases=cases,
        changes=changes,
        original_src_python_inventory=inventory,
        original_parser_predicates=predicates,
        parser_predicate_review=(
            "Exact original 22 query identities: no quarter/half/OT or reported reason; "
            "old/current opponent introductions identical. Old fragments extracted from the"
            " full parser file bound by original SHA."
        ),
        fresh_deployment_accepted=False,
        full_core1_accepted=False,
        current_snapshot_accepted=False,
        public_or_NBA_requests=0,
        production_writes=0,
        acceptance_limit=(
            "Applicability of retained original 44 desktop/mobile HTTP/rendered captures "
            "only; no new deployment, source, freshness, cold/performance, all 46 K08 "
            "positives or full Core-1 acceptance."
        ),
    )
    output = EVIDENCE / "historical-applicability-20261110.json"
    output.write_text(json.dumps(proof, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                path=str(output.relative_to(ROOT)),
                sha256=sha(output.read_bytes()),
                changed_files=len(changes),
                original_files=663,
                cases=22,
                captures=44,
            )
        )
    )


if __name__ == "__main__":
    main()
