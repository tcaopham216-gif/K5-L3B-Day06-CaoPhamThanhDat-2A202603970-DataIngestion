"""Persistent Chroma cosine HNSW (approximate) collections."""
import math
import chromadb
from .ingestion import BASE
class ChromaStore:
    def __init__(self,strategy,dimensions=384):
        self.dimensions=dimensions
        self.client=chromadb.PersistentClient(path=str(BASE/'chroma_db'))
        self.collection=self.client.get_or_create_collection('day6_'+('B' if strategy=='C' else strategy),metadata={'hnsw:space':'cosine'})
    def upsert(self,chunks,vectors):
        if len(chunks)!=len(vectors) or any(len(v)!=self.dimensions or not all(math.isfinite(x) for x in v) for v in vectors): raise ValueError('Invalid vector dimensions/values')
        for doc in sorted({c.document_id for c in chunks}):
            old=set(self.collection.get(where={'document_id':doc})['ids'])
            current={c.chunk_id for c in chunks if c.document_id==doc}
            stale=sorted(old-current)
            if stale: self.collection.delete(ids=stale)
        for start in range(0,len(chunks),128):
            batch=chunks[start:start+128]
            self.collection.upsert(ids=[c.chunk_id for c in batch],documents=[c.text for c in batch],embeddings=vectors[start:start+128],metadatas=[dict(**c.metadata,document_id=c.document_id,source=c.source,page=c.page) for c in batch])
    def search(self,query_vec,k=3,where=None):
        if len(query_vec)!=self.dimensions: raise ValueError('Invalid query dimension')
        r=self.collection.query(query_embeddings=[query_vec],n_results=k,where=where,include=['documents','distances','metadatas'])
        return [dict(id=i,text=t,score=1-d,metadata=m) for i,t,d,m in zip(r['ids'][0],r['documents'][0],r['distances'][0],r['metadatas'][0])]
