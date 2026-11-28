import hashlib
import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from nbatools.generation_manifest import GenerationFile
from nbatools.participation_source_packs import (
    INDEX,
    PACK_DIR,
    SOURCE_DIR,
    expanded_source_tree,
    pack_sources,
    read_source_index,
    unpack_sources,
)


def add(root, name, body):
    path = root / SOURCE_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path.relative_to(root).as_posix()


def inventory(root):
    return {
        path.relative_to(root).as_posix(): GenerationFile(
            path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()
        )
        for path in root.rglob("*")
        if path.is_file()
    }


def test_pack_is_deterministic_and_append_keeps_original_packs(tmp_path):
    roots = [tmp_path / "first", tmp_path / "same"]
    original = {}
    for root in roots:
        original = {
            add(root, "alpha.json", b"first body"): b"first body",
            add(root, "report.pdf", b"%PDF second body"): b"%PDF second body",
        }
        pack_sources(root, {})
    assert inventory(roots[0]) == inventory(roots[1])
    root = roots[0]
    initial = inventory(root)

    def reader(name):
        return (root / name).read_bytes()

    prior = read_source_index(initial, reader)
    newest = add(root, "new.json", b"another original")
    pack_sources(root, prior)
    final = inventory(root)
    assert all(final[path] == item for path, item in initial.items() if path != INDEX)
    index = read_source_index(final, reader)
    assert {name: index[name] for name in prior} == prior
    assert dict(unpack_sources(index, final, reader)) == {**original, newest: b"another original"}
    # A mixed generation keeps an untouched loose source for existing readers.
    loose = add(root, "loose.json", b"unpacked data")
    final = inventory(root)
    with expanded_source_tree(root, final, read_source_index(final, reader)) as view:
        assert (view / loose).read_bytes() == b"unpacked data"
        assert (view / newest).read_bytes() == b"another original"
    assert not (root / newest).exists()
    add(root, "new.json", b"conflicting logical owner")
    with pytest.raises(ValueError, match="overlapping"):
        read_source_index(inventory(root), reader)


@pytest.mark.parametrize("fault", ["tampered_index", "tampered_pack", "undeclared", "wrong_member"])
def test_bad_archive_or_member_fails_even_with_a_new_physical_manifest(tmp_path, fault):
    source = add(tmp_path, "evidence.json", b"exact source")
    index, _ = pack_sources(tmp_path, {})
    physical = inventory(tmp_path)
    original = tmp_path / index[source].pack

    def reader(name):
        return (tmp_path / name).read_bytes()

    if fault == "tampered_index":
        (tmp_path / INDEX).write_bytes(b"{}")
        with pytest.raises(ValueError, match="differ from their inventory"):
            read_source_index(physical, reader)
        return
    if fault == "tampered_pack":
        original.write_bytes(b"broken ZIP")
        with pytest.raises(ValueError, match="differ from their inventory"):
            dict(unpack_sources(index, physical, reader))
        return
    data = io.BytesIO()
    with ZipFile(data, "w", ZIP_DEFLATED) as zipped:
        zipped.writestr(
            Path(source).name, b"wrong source" if fault == "wrong_member" else b"exact source"
        )
        if fault == "undeclared":
            zipped.writestr("other.json", b"undeclared")
    raw = data.getvalue()
    pack = f"{PACK_DIR}/{hashlib.sha256(raw).hexdigest()}.zip"
    original.unlink()
    (tmp_path / pack).write_bytes(raw)
    doc = json.loads((tmp_path / INDEX).read_bytes())
    doc["files"][source]["pack"] = pack
    (tmp_path / INDEX).write_text(json.dumps(doc))
    physical = inventory(tmp_path)
    parsed = read_source_index(physical, reader)
    with pytest.raises(ValueError, match="inventory differs|differ from their inventory"):
        dict(unpack_sources(parsed, physical, reader))
