"""Run from starter: python -m src.run [--reload-check]."""
import argparse
import csv
import importlib.util
import json
import platform
import statistics
import sys
import time
from datetime import datetime,timezone
from importlib.metadata import version
from .ingestion import BASE,ingest
from .chunking import fixed_size,by_paragraph
from .evaluation import dump,evaluate,audits,csv_write

def verify_benchmark():
    spec=importlib.util.spec_from_file_location('verify_benchmark',BASE.parent/'benchmark/verify_benchmark.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.verify()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--reload-check',action='store_true');args=parser.parse_args()
    start=time.perf_counter();pages=ingest();ingest_seconds=time.perf_counter()-start
    questions=verify_benchmark() # Always validate frozen labels before any model/retrieval.
    from .embeddings import Embedder
    from .store import ChromaStore
    embed_start=time.perf_counter();embedder=Embedder();model_load_seconds=time.perf_counter()-embed_start
    chunk_sets={'A':fixed_size(pages),'B':by_paragraph(pages)};chunk_sets['C']=chunk_sets['B']
    stores={};vectors={};stats={};metrics={};traces={}
    for strategy in ('A','B'):
        start=time.perf_counter();chunks=chunk_sets[strategy]
        vectors[strategy]=embedder.documents([c.text for c in chunks]);stores[strategy]=ChromaStore(strategy)
        stores[strategy].upsert(chunks,vectors[strategy]);elapsed=time.perf_counter()-start
        lengths=[len(c.text) for c in chunks]
        stats[strategy]=dict(chunk_count=len(chunks),length_min=min(lengths),length_mean=statistics.mean(lengths),length_median=statistics.median(lengths),length_max=max(lengths),total_chars=sum(lengths),approx_tokens=sum(lengths)/4,ingest_embed_seconds=ingest_seconds+elapsed,embed_index_seconds=elapsed,source_ingest_seconds=ingest_seconds,cost=0)
    stores['C']=stores['B'];stats['C']={**stats['B'],'ingest_embed_seconds':0,'embed_index_seconds':0,'source_ingest_seconds':0,'shared_index':'B','resource_note':'Same chunks and index as B; no duplicate ingest/embedding charge.'}
    start=time.perf_counter();query_vectors=[embedder.query(q['question']) for q in questions];query_embedding_seconds=time.perf_counter()-start
    for strategy in ('A','B','C'):
        metrics[strategy],traces[strategy],seconds=evaluate(strategy,stores[strategy],questions,query_vectors)
        stats[strategy]['query_time_seconds']=seconds
        stats[strategy]['shared_query_embedding_seconds']=query_embedding_seconds
    dump('metrics.json',metrics);dump('ingest_stats.json',stats)
    table=['| Strategy | Split | Hit@1 | Evidence Hit@3 |','|---|---|---|---|']
    for strategy in ('A','B','C'):
        for split in ('dev','test'):
            values=[metrics[strategy][split][key] for key in ('Hit@1','Evidence Hit@3')]
            table.append(f"| {strategy} | {split} | "+' | '.join(f"{v['numerator']}/{v['denominator']} ({v['rate']:.1%})" for v in values)+' |')
    (BASE/'results/metrics.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
    dump('run_info.json',dict(python=sys.version,platform=platform.platform(),libraries={k:version(k) for k in ('chromadb','fastembed','onnxruntime','numpy')},**embedder.info,timestamp=datetime.now(timezone.utc).isoformat(),model_load_seconds=model_load_seconds,hnsw_approximate=True,metric='cosine',store_path=str(BASE/'chroma_db'),collections=['day6_A','day6_B'],document_embedding='embed',query_embedding='query_embed',chunking=dict(A=dict(size=500,overlap=50),B=dict(max_chars=1200,min_chars=200)),backend_note='Chroma selected because pgvector/Docker are unavailable on this machine.',cost=0))
    audits(pages,chunk_sets,traces)
    hypotheses={'A':'Short windows may focus retrieval but cut evidence at boundaries.','B':'Paragraph grouping may preserve more complete evidence with larger context.','C':'User-supplied book scope may reduce cross-book ambiguity relative to B.'}
    rows=[]
    for strategy in ('A','B','C'):
        row=dict(strategy=strategy,chunking='fixed_size' if strategy=='A' else 'by_paragraph',chunk_size=500 if strategy=='A' else 1200,overlap=50 if strategy=='A' else 0,metadata='source,page,book,chapter,offsets',filter='question input only' if strategy=='C' else 'none',vectorizer=embedder.info['model'],hypothesis=hypotheses[strategy],notes='Manual audit labels pending; small held-out chapter sample; HNSW approximate.')
        for split in ('dev','test'):
            for suffix,key in [('hit1','Hit@1'),('hit3','Evidence Hit@3')]:
                v=metrics[strategy][split][key];row[f'{split}_{suffix}']=f"{v['numerator']}/{v['denominator']}"
        rows.append(row)
    csv_write(BASE.parent/'artifacts/experiment_log.csv',list(rows[0]),rows)
    if args.reload_check:
        before={s:stores[s].collection.count() for s in ('A','B')}
        second_pages=ingest();second={'A':fixed_size(second_pages),'B':by_paragraph(second_pages)}
        for s in ('A','B'):
            assert [(c.chunk_id,c.text,c.metadata) for c in second[s]]==[(c.chunk_id,c.text,c.metadata) for c in chunk_sets[s]]
            # Identical text/model: reuse real embeddings for the second upsert.
            ChromaStore(s).upsert(second[s],vectors[s])
        after={s:ChromaStore(s).collection.count() for s in ('A','B')}
        expected={s:len(second[s]) for s in ('A','B')}
        assert before==after==expected,(before,after,expected)
        dump('reload_check.json',dict(before=before,after=after,expected=expected,passed=True,ingestion_passes=2,note='Second ingest reproduced IDs, text and metadata; persisted collections reopened. C reuses B. Real embeddings reused for identical inputs.'))
    installed='\n'.join(f'{k}=={version(k)}' for k in ('chromadb','fastembed'))+'\n'
    (BASE/'requirements.txt').write_text(installed,encoding='utf-8')
    print('\n'.join(table));print('Manual audit CSVs intentionally have empty labels.')

if __name__=='__main__': main()
