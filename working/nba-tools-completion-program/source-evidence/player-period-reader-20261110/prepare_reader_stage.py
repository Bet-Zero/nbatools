"""Metadata-only qualification companion for unchanged PR602 v5 source inputs."""

import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from nbatools.commands.aggregate_metrics import METRIC_DESCRIPTORS, AggregationKind
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, sha256
from tools.development_snapshot import write_json

E = Path(__file__).resolve().parent
PARENT = E.parent / "current123-periods-20261107"
VERSION = "current123-period-reader-development-v6"


def prepare(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    binding = json.loads((PARENT / "v5-binding.json").read_bytes())
    original = (PARENT / binding["archive"]).read_bytes()
    assert sha256(original) == binding["archive_sha256"] == "3f00e20684617dc33777fe151b61cf5d9dc91da46661c53572c608caf6102aa5"
    root = output / "stage"
    with ZipFile(io.BytesIO(original)) as z:
        assert all(n.startswith("data/") and ".." not in Path(n).parts for n in z.namelist())
        z.extractall(root)
    prior = DevelopmentSnapshot(root, binding["manifest_sha256"])
    parent_raw = (root / MANIFEST).read_bytes()
    parent_path = "data/metadata/period-reader-origin.json"
    (root / parent_path).write_bytes(parent_raw)
    dataset = "data/raw/player_game_period_stats/2026-27_regular_season.csv"
    frame = pd.read_csv(root / dataset)
    overtime = frame.loc[frame.period_family.eq("overtime"), ["game_id", "team_id", "player_id"]]
    keys = sorted([list(map(int, row)) for row in overtime.itertuples(index=False, name=None)])
    assert len(keys) == 97 and len(frame) == 16783
    assert frame[["usg_pct", "tov_pct"]].isna().sum().to_dict() == {"usg_pct":242,"tov_pct":242}
    proof = dict(schema_version=1,kind="player_period_inputs",dataset_path=dataset,
        dataset_sha256=sha256((root/dataset).read_bytes()),
        origin_manifest_path=parent_path,origin_manifest_sha256=sha256(parent_raw),
        deferred_columns=sorted(k for k,v in METRIC_DESCRIPTORS.items() if v.kind==AggregationKind.AVERAGE_ONLY),
        overtime_player_keys=keys,
        source_qualification=dict(
            reference="working/nba-tools-completion-program/source-evidence/current123-periods-20261107/independent-v5-review.md",
            sha256=sha256((PARENT/"independent-v5-review.md").read_bytes()),
            original_capture_sha256="81eea4d32217e541cab13783a06031616abb192e56b7c7b37d10f1f460978faf",
            accepted_v5_archive_sha256=binding["archive_sha256"],
            accepted_v5_manifest_sha256=binding["manifest_sha256"],required_numerical_run=42371619251,
            complete_input_scope="PR602 complete count/clock/key and non-null source-rate inputs; exact original484rate nulls remain unknown"),
        production_accepted=False,source_values_changed=False)
    report_path="data/metadata/player-period-input-qualification.json"
    report_sha=write_json(root/report_path,proof)
    doc=dict(prior.document,version=VERSION,
        scope="Unchanged source-qualified PR602 v5 rows; rate dependencies checked per complete query sample; old484unknowns/DQ006/freshness/publication remain open",
        validation_reports=[*prior.document["validation_reports"],dict(kind="player_period_inputs",dataset_path=dataset,path=report_path,sha256=report_sha,state="qualified_inputs")])
    doc["files"]={p.relative_to(root).as_posix():sha256(p.read_bytes()) for p in sorted((root/"data").rglob("*")) if p.is_file() and p.relative_to(root)!=MANIFEST}
    digest=write_json(root/MANIFEST,doc)
    DevelopmentSnapshot(root,digest)
    for path,expected in prior.files.items():
        assert sha256((root/path).read_bytes())==expected
    archive=output/"current123-period-reader-v6.zip"
    with ZipFile(archive,"x",ZIP_DEFLATED) as z:
        for p in sorted((root/"data").rglob("*")):
            if p.is_file():z.write(p,p.relative_to(root).as_posix())
    result=dict(archive=archive.name,archive_sha256=sha256(archive.read_bytes()),manifest_sha256=digest,
        parent_manifest_sha256=binding["manifest_sha256"],source_values_changed=False,old_unknowns=484,production_writes=0)
    write_json(output/"binding.json",result)
    return result


if __name__=="__main__":
    import sys
    print(json.dumps(prepare(Path(sys.argv[1])),indent=2))
