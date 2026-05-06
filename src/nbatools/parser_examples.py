from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "docs/architecture/parser/examples.md"


@dataclass(frozen=True)
class Case:
    case_id: str
    source_section: str
    source_subsection: str
    case_kind: str
    query_text: str
    expected_behavior_category: str
    expected_notes: str
    pair_key: str = ""
    equivalence_group: str = ""


def slug_subsection(title: str) -> str:
    match = re.match(r"^(\d+(?:\.\d+)*)", title)
    if not match:
        return "unknown"
    return match.group(1).replace(".", "_")


def clean_query(text: str) -> str:
    text = text.strip()
    text = text.strip("|")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def md_section(lines: list[str], start: str, end: str | None) -> list[str]:
    start_idx = next(i for i, line in enumerate(lines) if line.startswith(start))
    if end is None:
        end_idx = len(lines)
    else:
        end_idx = next(
            i
            for i, line in enumerate(lines[start_idx + 1 :], start_idx + 1)
            if line.startswith(end)
        )
    return lines[start_idx:end_idx]


def expected_for(query: str, section: str, subsection: str) -> tuple[str, str]:
    q = query.lower()
    sub = subsection.lower()
    boundary_terms = (
        "clutch",
        "4th quarter",
        "fourth quarter",
        "first half",
        "second half",
        "overtime",
        "back-to-back",
        "back to back",
        "b2b",
        "rest advantage",
        "rest disadvantage",
        "2 days rest",
        "one-possession",
        "one possession",
        "national tv",
        "nationally televised",
        "starter",
        "starting",
        "off the bench",
        "on/off",
        "on off",
        "on-off",
        "on the floor",
        "off the floor",
        "with and without",
        "lineup",
        "lineups",
        "units",
        "together",
    )
    opponent_quality_terms = (
        "contenders",
        "good teams",
        "top teams",
        "playoff teams",
        "teams over .500",
        "teams above .500",
        "top-10 defenses",
        "top 10 defenses",
        "top defenses",
        "winning teams",
        "top-5 offenses",
        "elite frontcourts",
        "above .600",
    )
    future_or_unsupported = (
        "co-star",
        "star teammate",
        "leading scorer",
        "cooled off",
        "best defense recently",
        "best net rating in its last",
        "averaged a double-double",
        "drop-off",
        "catch-and-shoot",
        "catch and shoot",
        "drawing fouls",
        "transition scorer",
        "isolation defender",
        "shot creator",
        "paint points",
        "biggest triple-double",
        "attempts per game",
        "two-way",
        "all-around",
        "all around",
        "rebounding battle",
        "leads the team in scoring",
        "both play",
        "trailing after 3 quarters",
        "10+ assists and 0 turnovers",
        "offensive rating when",
        "offensive rating without",
        "road by 20",
        "road team won by 20",
        "at __",
        "___",
        "since becoming a starter",
        "elite frontcourts",
    )

    if section.startswith("5."):
        if "ambiguous references" in sub or "ambiguous intent" in sub:
            return "ambiguous_expected", "Stress subsection documents this as ambiguous."
        return (
            "stress_clean_failure_ok",
            "Stress input; clean routed result, ambiguity, no-result, or unsupported response is acceptable.",
        )

    if section.startswith("8.1") or subsection.startswith("8.1"):
        return (
            "unsupported_expected",
            "Section 8.1 marks these as future expansion requiring new definitions or sources.",
        )
    if section.startswith("8.5") or subsection.startswith("8.5"):
        return "unsupported_expected", "Section 8.5 is a future expansion-pattern boundary."

    if any(term in q for term in future_or_unsupported):
        return (
            "unsupported_expected",
            "Examples/reference docs mark this broader semantic family as unsupported or outside the core finish line.",
        )

    if any(term in q for term in boundary_terms):
        return (
            "supported_with_fallback",
            "Context/source-backed family is coverage-gated or can carry an explicit unfiltered/unsupported-data note.",
        )

    if any(term in q for term in opponent_quality_terms):
        if any(term in q for term in ("top-5 offenses", "elite frontcourts", "above .600")):
            return (
                "unsupported_expected",
                "Opponent-quality variant is documented as future expansion.",
            )
        return (
            "supported_with_fallback",
            "Opponent-quality filters are supported on core single-entity routes; unsupported routes should note unfiltered behavior.",
        )

    if section.startswith("7.7") or section.startswith("7.8") or section.startswith("7.9"):
        return (
            "supported_with_fallback",
            "Equivalence group includes an explicit coverage-gated or unfiltered execution note.",
        )
    if section.startswith("7.10") or section.startswith("7.11") or section.startswith("7.12"):
        return (
            "supported_with_fallback",
            "Equivalence group includes an explicit coverage-gated execution note.",
        )
    if section.startswith("7.13") or section.startswith("7.14") or section.startswith("7.15"):
        return (
            "supported_with_fallback",
            "Equivalence group includes an explicit coverage-gated or unsupported-data execution note.",
        )
    if section.startswith("7.16") or section.startswith("7.17"):
        return "supported_with_fallback", "Lineup equivalence group is source-coverage gated."
    if (
        section.startswith("8.2")
        or section.startswith("8.3")
        or subsection.startswith("8.2")
        or subsection.startswith("8.3")
    ):
        return (
            "supported_with_fallback",
            "Expansion boundary is shipped only inside documented coverage-gated route boundaries.",
        )

    return (
        "supported_exact",
        "Documented shipped query surface or canonical parser example without an explicit fallback/unsupported note.",
    )


def add_case(
    cases: list[Case],
    case_id: str,
    section: str,
    subsection: str,
    kind: str,
    query: str,
    pair_key: str = "",
    equivalence_group: str = "",
) -> None:
    query = clean_query(query)
    if not query:
        return
    category, notes = expected_for(query, section, subsection)
    cases.append(
        Case(
            case_id=case_id,
            source_section=section,
            source_subsection=subsection,
            case_kind=kind,
            query_text=query,
            expected_behavior_category=category,
            expected_notes=notes,
            pair_key=pair_key,
            equivalence_group=equivalence_group,
        )
    )


def extract_cases() -> list[Case]:
    lines = SOURCE_PATH.read_text().splitlines()
    cases: list[Case] = []

    current_sub = ""
    sub_counts: Counter[str] = Counter()
    for line in md_section(lines, "## 2.", "## 3."):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        match = re.match(r"^(\d+)\.\s+(.+)$", line)
        if match and current_sub:
            slug = slug_subsection(current_sub)
            sub_counts[slug] += 1
            add_case(
                cases,
                f"S2_{slug}_{sub_counts[slug]:02d}",
                "2. Canonical example set",
                current_sub,
                "canonical_numbered",
                match.group(2),
            )

    current_sub = ""
    for line in md_section(lines, "## 3.", "## 4."):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        if not line.startswith("|"):
            continue
        cells = [clean_query(c) for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or not cells[0].isdigit():
            continue
        slug = slug_subsection(current_sub)
        pair_num = int(cells[0])
        pair_key = f"S3_{slug}_{pair_num:02d}"
        add_case(
            cases,
            f"{pair_key}_Q",
            "3. Paired examples",
            current_sub,
            "paired_question",
            cells[1],
            pair_key=pair_key,
        )
        add_case(
            cases,
            f"{pair_key}_S",
            "3. Paired examples",
            current_sub,
            "paired_search",
            cells[2],
            pair_key=pair_key,
        )

    current_sub = ""
    sub_counts = Counter()
    for line in md_section(lines, "## 4.", "## 5."):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        if not line.startswith("- "):
            continue
        queries = re.findall(r"`([^`]+)`", line)
        for query in queries:
            slug = slug_subsection(current_sub)
            sub_counts[slug] += 1
            add_case(
                cases,
                f"S4_{slug}_{sub_counts[slug]:02d}",
                "4. Capability clusters",
                current_sub,
                "cluster_bullet",
                query,
            )

    current_sub = ""
    sub_counts = Counter()
    for line in md_section(lines, "## 5.", "## 6."):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        if not line.startswith("- "):
            continue
        queries = re.findall(r"`([^`]+)`", line)
        for query in queries:
            parts = [clean_query(part) for part in re.split(r"\s+/\s+", query)]
            if len(parts) > 1:
                for part in parts:
                    slug = slug_subsection(current_sub)
                    sub_counts[slug] += 1
                    add_case(
                        cases,
                        f"S5_{slug}_{sub_counts[slug]:02d}",
                        "5. Stress test inputs",
                        current_sub,
                        "stress_fragment",
                        part,
                    )
            else:
                slug = slug_subsection(current_sub)
                sub_counts[slug] += 1
                add_case(
                    cases,
                    f"S5_{slug}_{sub_counts[slug]:02d}",
                    "5. Stress test inputs",
                    current_sub,
                    "stress_input",
                    query,
                )

    current_sub = ""
    sub_counts = Counter()
    for line in md_section(lines, "## 6.", "## 7."):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        match = re.match(r"^\*\*Raw input:\*\*\s+`([^`]+)`", line)
        if match:
            slug = slug_subsection(current_sub)
            sub_counts[slug] += 1
            add_case(
                cases,
                f"S6_{slug}_{sub_counts[slug]:02d}",
                "6. End-to-end worked examples",
                current_sub,
                "worked_raw_input",
                match.group(1),
            )

    current_sub = ""
    sub_counts = Counter()
    for line in md_section(lines, "## 7.", "## 8."):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        if not line.startswith("- ") or line.startswith("- _"):
            continue
        queries = re.findall(r"`([^`]+)`", line)
        for query in queries:
            slug = slug_subsection(current_sub)
            sub_counts[slug] += 1
            add_case(
                cases,
                f"S7_{slug}_{sub_counts[slug]:02d}",
                f"7.{slug.split('_', 1)[1] if '_' in slug else ''} Equivalence groups",
                current_sub,
                "equivalence_member",
                query,
                equivalence_group=f"S7_{slug}",
            )

    current_sub = ""
    sub_counts = Counter()
    for line in md_section(lines, "## 8.", None):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        if not line.startswith("- "):
            continue
        if line.startswith("- _") or "See equivalence" in line or "specification.md" in line:
            continue
        queries = re.findall(r"`([^`]+)`", line)
        for query in queries:
            if query.startswith("specification.md") or query in {
                "team_record",
                "player_game_summary",
                "player_game_finder",
            }:
                continue
            slug = slug_subsection(current_sub)
            sub_counts[slug] += 1
            add_case(
                cases,
                f"S8_{slug}_{sub_counts[slug]:02d}",
                "8. Expansion patterns and explicit boundaries",
                current_sub,
                "boundary_example",
                query,
            )

    seen: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            raise RuntimeError(f"duplicate case id: {case.case_id}")
        seen.add(case.case_id)
    return cases
