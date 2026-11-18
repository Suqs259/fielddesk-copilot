"""Deterministic retrieval evaluation; not a claim of real-world answer quality."""
import json
from pathlib import Path
from app.core import retrieve

cases = json.loads(Path('data/eval.json').read_text(encoding='utf-8'))
hits = leaks = 0
for case in cases:
    docs = retrieve(case['question'], case['tenant'])
    ids = {d['id'] for d in docs}
    hits += bool(ids.intersection(case['expected']))
    leaks += sum(d['tenant'] not in ('public', case['tenant']) for d in docs)
report = {'cases':len(cases), 'hit_at_3':round(hits/len(cases), 3), 'unauthorized_documents':leaks,
          'scope':'Synthetic retrieval smoke benchmark; not an LLM or production quality score.'}
print(json.dumps(report, ensure_ascii=False, indent=2))
if leaks or hits != len(cases):
    raise SystemExit(1)
