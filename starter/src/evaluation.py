"""Evidence retrieval metrics and unlabelled manual-audit exports."""
import csv
import json
import time
from .ingestion import BASE

def norm(s): return ' '.join(s.split())
def dump(name,obj):
    (BASE/'results'/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def csv_write(path,fields,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def evaluate(strategy,store,questions,query_vectors):
    traces=[];start=time.perf_counter()
    for q,v in zip(questions,query_vectors):
        filt=q['filter'] if strategy=='C' else None
        top=store.search(v,k=3,where=filt)
        for r in top:
            r['hit']=r['metadata']['page_id'] in q['gold_page'] and norm(q['evidence_quote']) in norm(r['text'])
            r['evidence_split_across_chunks']=r['metadata']['page_id'] in q['gold_page'] and not r['hit']
        traces.append(dict(question_id=q['id'],question=q['question'],split=q['split'],filter=q['filter'],filter_applied=bool(filt),gold_page=q['gold_page'],evidence_quote=q['evidence_quote'],expected_answer=q['expected_answer'],top3=top,hit_at_1=top[0]['hit'],evidence_hit_at_3=any(r['hit'] for r in top),problems=['evidence split across chunks (gold page retrieved without complete quote)'] if any(r['evidence_split_across_chunks'] for r in top) else []))
    elapsed=time.perf_counter()-start
    (BASE/'results'/f'traces_{strategy}.jsonl').write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in traces),encoding='utf-8')
    metrics={}
    for split in ('dev','test'):
        ts=[t for t in traces if t['split']==split];n=len(ts)
        metrics[split]={key:dict(numerator=sum(t[field] for t in ts),denominator=n,rate=sum(t[field] for t in ts)/n) for key,field in [('Hit@1','hit_at_1'),('Evidence Hit@3','evidence_hit_at_3')]}
    return metrics,traces,elapsed

def audits(pages,chunk_sets,traces):
    rows=[]
    positions=[p for p in pages if p.page<=5]
    assert len(positions)==10
    for p in positions:
        position=min(300,len(p.text)-1)
        for strategy,chunks in chunk_sets.items():
            matches=[c for c in chunks if c.metadata['page_id']==p.metadata['page_id'] and c.metadata['chunk_char_start']<=position<c.metadata['chunk_char_end']]
            assert matches,(strategy,p.metadata['page_id'])
            c=matches[0]
            rows.append(dict(strategy=strategy,position_id=f"{p.metadata['page_id']}@{p.metadata['char_start']+position}",chunk_id=c.chunk_id,chunk_text=c.text,score_0_2='',reason=''))
    csv_write(BASE/'results/audit_template_coherence.csv',['strategy','position_id','chunk_id','chunk_text','score_0_2','reason'],rows)
    rows=[]
    for strategy,ts in traces.items():
        for t in ts:
            if t['split']!='test': continue
            for rank,r in enumerate(t['top3'],1):
                m=r['metadata']
                rows.append(dict(question_id=t['question_id'],question=t['question'],strategy=strategy,rank=rank,chunk_id=r['id'],source=m['source'],page=m['page'],page_id=m['page_id'],chapter=m['chapter_title'],text=r['text'],metadata_correct='',filter_ok='',grounding_0_2='',reason=''))
    csv_write(BASE/'results/audit_template_test.csv',['question_id','question','strategy','rank','chunk_id','source','page','page_id','chapter','text','metadata_correct','filter_ok','grounding_0_2','reason'],rows)
