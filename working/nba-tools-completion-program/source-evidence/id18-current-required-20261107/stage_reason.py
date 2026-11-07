"""Offline ID18 version using existing structured/reason producers and retained bytes."""
import json
import shutil
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from nbatools.commands.pipeline import reported_absence_reasons as producer
from nbatools.commands.pipeline.structured_participation import stage_structured_game, validate_structured_import
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, sha256
from tools.development_snapshot import write_json

ROOT = Path(__file__).resolve().parents[4]
E = Path(__file__).resolve().parent
PREVIOUS = E.parent / 'core-live-current-20261107'
SUFFIX = '2026-27_regular_season.csv'
GID = 22600143


def stage(work: Path, output: Path):
    if work.exists() or output.exists():
        raise ValueError('Use new work and snapshot destinations')
    archive = (PREVIOUS / 'current123-provisional.zip').read_bytes()
    assert sha256(archive) == 'eb60f64204a089d0d5a9083496aa44e172e3fe511b71d7980a0649e0e3778c17'
    with ZipFile(PREVIOUS / 'current123-provisional.zip') as z:
        z.extractall(work / 'v1')
    old = work / 'v1'
    base_sha = sha256((old / MANIFEST).read_bytes())
    DevelopmentSnapshot(old, base_sha)
    shutil.copytree(old, output)
    sources = work / 'sources'
    sources.mkdir()
    original = (PREVIOUS / 'current-originals.zip').read_bytes()
    assert sha256(original) == '411435a52ba299441e06cc0af50bfd4e31da7e853d0dc2cd03fe197e13a695dd'
    with ZipFile(PREVIOUS / 'current-originals.zip') as z:
        custody_raw = z.read('retained-pairs/source-custody.json')
        custody = [r for r in json.loads(custody_raw) if r['game_id'] == '0022600143']
        assert len(custody) == 2
        for item in custody:
            raw = z.read('retained-pairs/sources/' + item['file'])
            assert sha256(raw) == item['sha256'] and len(raw) == item['size_bytes']
            (sources / item['file']).write_bytes(raw)
    # Recover the exact identity packet with the existing source producer and
    # the immutable revision/equivalence receipt;
    # neither original capture times nor the old version are overwritten.
    canonical = work / 'canonical'
    for family in ['games', 'team_game_stats', 'player_game_stats']:
        path = Path('raw') / family / SUFFIX
        (canonical / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(old / 'data' / path, canonical / path)
    times = {r['verified_at'] for r in custody}
    revision, = {r['bound_revision'] for r in custody}
    rows = stage_structured_game(
        canonical, season='2026-27', season_type='Regular Season', game_id=GID,
        traditional=sources / 'boxscoretraditionalv3_0022600143.json',
        summary=sources / 'boxscoresummaryv3_0022600143.json', summary_version=3,
        revision=revision, retrieved_at=max(times),
    )
    binary = Path('raw/player_game_availability') / SUFFIX
    before = pd.read_csv(old / 'data' / binary)
    prior = before.loc[before.game_id.eq(GID)].sort_values(['team_id', 'player_id']).reset_index(drop=True)
    now = rows.sort_values(['team_id', 'player_id']).reset_index(drop=True)
    for col in before.columns:
        if col != 'source_sha256':
            pd.testing.assert_series_equal(prior[col].fillna(""), now[col].fillna(""), check_dtype=False, check_names=False)
    # Preserve all original rows and literal CSV tokens, changing only the new
    # source packet digest only if needed after complete semantic equality.
    # In this retained package it matches exactly: all binary bytes survive.
    digest, = set(rows.source_sha256)
    text = (old / 'data' / binary).read_text()
    prior_digest, = set(prior.source_sha256)
    assert text.count(prior_digest) == len(prior)
    (output / 'data' / binary).write_text(text.replace(prior_digest, digest))
    shutil.copyfile(canonical / binary.with_suffix('.imports.json'), output / 'data' / binary.with_suffix('.imports.json'))
    shutil.copytree(canonical / 'raw/player_game_availability_sources', output / 'data/raw/player_game_availability_sources')
    actual = pd.read_csv(output / 'data' / binary)
    imports = json.loads((output / 'data' / binary.with_suffix('.imports.json')).read_bytes())
    validate_structured_import(output / 'data', GID, actual.loc[actual.game_id.eq(GID)], imports[str(GID)])
    # Canonical adapter receipt records the original capture, with explicit link
    # back to its unchanged capture.json. It does not recapture or backdate data.
    capture_raw = (PREVIOUS / 'luka-report/capture.json').read_bytes()
    cap = json.loads(capture_raw)
    pdf = PREVIOUS / 'luka-report/original.pdf'
    assert sha256(pdf.read_bytes()) == cap['sha256_of_bytes_read']
    receipt = dict(source_url=cap['source_url'], sha256=cap['sha256_of_bytes_read'],
                   size_bytes=cap['bytes_read'], raw_file=cap['sha256_of_bytes_read'] + '.pdf',
                   retrieved_at=cap['finished_at'], original_capture_sha256=sha256(capture_raw))
    write_json(sources / 'pdf-receipt.json', receipt)
    observed = producer.stage_observation(
        output / 'data', season='2026-27', season_type='Regular Season', game_id=GID,
        team_id=1610612747, player_id=1629029, source_kind='nba_official_finalbox',
        source_file=pdf, source_receipt=sources / 'pdf-receipt.json')
    assert observed['reported_reason'] == 'reported_other'
    producer.validate_publication(output / 'data')
    write_json(output / 'data/metadata/id18-source-custody.json', dict(
        base_manifest_sha256=base_sha, original_custody_sha256=sha256(custody_raw),
        original_capture_sha256=sha256(capture_raw), exact_game_custody=custody,
        identity_packet_recovered_exact=(prior_digest == digest), changed_binary_fields=[] if prior_digest == digest else ['source_sha256'],
        old_packet_sha256=prior_digest, new_packet_sha256=digest, production_writes=0))
    doc = json.loads((old / MANIFEST).read_bytes())
    doc.update(version='current123-id18-reason-development-v2',
               source_evidence=dict(reference=str(E.relative_to(ROOT)), sha256=sha256(original)),
               scope=doc['scope'] + '; full9LAL Luka reported Rest0, other1, unknown0; canonical source companion replayed')
    doc['files'] = {p.relative_to(output).as_posix(): sha256(p.read_bytes())
                    for p in sorted((output / 'data').rglob('*')) if p.is_file() and p.relative_to(output) != MANIFEST}
    result_sha = write_json(output / MANIFEST, doc)
    DevelopmentSnapshot(output, result_sha)
    return result_sha


if __name__ == '__main__':
    import sys
    print(stage(Path(sys.argv[1]), Path(sys.argv[2])))
