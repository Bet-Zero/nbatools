from pathlib import Path

from tools import check_docs_governance


def test_audit_markdown_is_discovered_for_link_only_governance(tmp_path: Path, monkeypatch) -> None:
    audit = tmp_path / "docs" / "audits" / "example.md"
    audit.parent.mkdir(parents=True)
    audit.write_text("historical snapshot\n", encoding="utf-8")
    monkeypatch.setattr(check_docs_governance, "ROOT", tmp_path)

    assert check_docs_governance.link_only_files() == [Path("docs/audits/example.md")]


def test_audit_link_governance_rejects_broken_relative_target(tmp_path: Path, monkeypatch) -> None:
    audit = Path("docs/audits/example.md")
    audit_path = tmp_path / audit
    audit_path.parent.mkdir(parents=True)
    text = "[engine](../../src/nbatools/engine.py)\n"
    audit_path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(check_docs_governance, "ROOT", tmp_path)

    errors = check_docs_governance.check_relative_links(audit, text)

    assert errors == [
        "docs/audits/example.md:1: broken relative Markdown link: ../../src/nbatools/engine.py"
    ]


def test_audit_link_governance_accepts_existing_relative_target(
    tmp_path: Path, monkeypatch
) -> None:
    audit = Path("docs/audits/example.md")
    audit_path = tmp_path / audit
    target = tmp_path / "src" / "nbatools" / "engine.py"
    audit_path.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    target.write_text("", encoding="utf-8")
    text = "[engine](../../src/nbatools/engine.py#L1)\n"
    audit_path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(check_docs_governance, "ROOT", tmp_path)

    assert check_docs_governance.check_relative_links(audit, text) == []


def test_main_applies_link_governance_to_audit_markdown(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    audit = tmp_path / "docs" / "audits" / "example.md"
    audit.parent.mkdir(parents=True)
    audit.write_text("[missing](../../src/missing.py)\n", encoding="utf-8")
    monkeypatch.setattr(check_docs_governance, "ROOT", tmp_path)
    monkeypatch.setattr(check_docs_governance, "check_docs_layout", lambda: [])
    monkeypatch.setattr(check_docs_governance, "durable_files", lambda: [])
    monkeypatch.setattr(check_docs_governance, "tracked_output_dependency_files", lambda: [])

    assert check_docs_governance.main() == 1
    assert "broken relative Markdown link: ../../src/missing.py" in capsys.readouterr().out
