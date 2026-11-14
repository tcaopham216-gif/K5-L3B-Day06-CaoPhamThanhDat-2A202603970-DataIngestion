"""Verify frozen evidence against regenerated normalized source units."""
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def normalized(s): return ' '.join(s.split())
def verify():
    units={p['page_id']:p for p in map(json.loads,(ROOT/'starter/data/units.jsonl').read_text(encoding='utf-8').splitlines())}
    questions=list(map(json.loads,(ROOT/'benchmark/questions.jsonl').read_text(encoding='utf-8').splitlines()))
    assert len(questions)>=22 and len({q['id'] for q in questions})==len(questions)
    assert sum(q['split']=='dev' for q in questions)>=16
    assert sum(q['split']=='test' for q in questions)>=6
    assert sum(bool(q['filter']) for q in questions)>=4
    assert sum(bool(q['filter']) and q['split']=='test' for q in questions)>=2
    report=[]
    for q in questions:
        assert q['gold_page'] and 40<=len(q['evidence_quote'])<=250,q['id']
        assert q['type'] in {'direct','paraphrased','condition'}
        assert q['filter'] is None or q['filter']=={'book':q['gold_source_id']}
        for pid in q['gold_page']:
            p=units[pid]
            assert p['document_id']==q['gold_source_id'],q['id']
            assert normalized(q['evidence_quote']) in normalized(p['text']),(q['id'],pid)
        report.append(f"PASS {q['id']} ({q['split']}): {', '.join(q['gold_page'])}")
    report.append(f'All {len(questions)} questions passed; evidence is case-sensitive and whitespace-normalized.')
    target=ROOT/'starter/results/benchmark_verification.txt';target.parent.mkdir(exist_ok=True)
    target.write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('\n'.join(report))
    return questions
if __name__=='__main__': verify()
