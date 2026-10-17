"""Restore losslessly packed original receipts and verify their recorded hashes."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).parent
packed = json.loads((root / 'receipts.json').read_text())
expected = json.loads((root / 'evaluation.json').read_text())['receipt_sha256']
(root / 'receipts').mkdir(exist_ok=True)
for filename, item in packed.items():
    rows = []
    for run in item['runs']:
        timing = {key: value for key, value in run.items() if key != 'answer_index'}
        rows.append(dict(**timing, **item['answers'][run['answer_index']]))
    content = json.dumps(rows, indent=2, default=str)
    assert hashlib.sha256(content.encode()).hexdigest() == expected[filename], filename
    (root / 'receipts' / filename).write_text(content)
print(f'Restored and hash-verified {len(packed)} receipts.')
