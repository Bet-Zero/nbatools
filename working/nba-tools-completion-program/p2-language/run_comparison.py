"""Finite frozen experiment; execution receipts, no production modifications."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).parent

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def worker(index, path):
    from candidate import interpret
    from nbatools.query_service import execute_natural_query
    from nbatools.commands import team_record, team_split_summary, player_split_summary
    h = json.loads((ROOT / 'holdouts.json').read_text())
    case = (h['valid_cases'] + h['controls'])[index]
    captured = []
    def wrap(original):
        def call(frame, *args, **kwargs):
            keys = [k for k in ['game_id', 'team_id', 'player_id'] if k in frame]
            captured.append({'bucket': str(args[0]) if args else None,
                             'ids': frame[keys].astype(int).to_dict('records')})
            return original(frame, *args, **kwargs)
        return call
    team_record._compute_record = wrap(team_record._compute_record)
    team_split_summary._summarize_bucket = wrap(team_split_summary._summarize_bucket)
    player_split_summary._summarize_bucket = wrap(player_split_summary._summarize_bucket)
    receipts = []
    for repetition in range(4):
        captured.clear()
        start = time.perf_counter()
        try:
            query = interpret(case['query']) if path == 'candidate' else case['query']
            response = execute_natural_query(query)
            elapsed = time.perf_counter() - start
            result = response.result.to_dict()
            receipts.append({'repetition': repetition, 'cache': 'cold-process' if repetition == 0 else 'warm',
                'seconds': elapsed, 'interpreted_query': query, 'status': response.result_status,
                'route': response.route, 'metadata': response.metadata,
                'result': result, 'captured_samples': list(captured)})
        except Exception as exc:
            receipts.append({'repetition': repetition, 'seconds': time.perf_counter()-start,
                             'error': type(exc).__name__ + ': ' + str(exc)})
    (ROOT / 'receipts' / f"{case['id']}-{path}.json").write_text(json.dumps(receipts, indent=2, default=str))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', type=int)
    parser.add_argument('--path')
    args = parser.parse_args()
    if args.worker is not None:
        worker(args.worker, args.path)
    else:
        h = json.loads((ROOT / 'holdouts.json').read_text())
        assert digest(ROOT/'candidate.py') == h['candidate_frozen_sha256']
        assert digest(ROOT/'holdouts.json') == 'd65cf93f47b03bd9263105ecb91bb3e4936e73c9bbfb5a08d2261bbab39c1027'
        for filename, expected in h['source_sha256'].items():
            assert digest(filename) == expected, filename
        (ROOT/'receipts').mkdir(exist_ok=True)
        for index, case in enumerate(h['valid_cases'] + h['controls']):
            for path in ['incumbent', 'candidate']:
                subprocess.run([sys.executable, __file__, '--worker', str(index), '--path', path], check=True)
            print(case['id'], 'recorded', flush=True)
