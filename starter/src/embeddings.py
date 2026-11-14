"""Real local BGE embeddings; failures propagate without fallback."""
from importlib.metadata import version
from fastembed import TextEmbedding
from .ingestion import BASE
MODEL='BAAI/bge-small-en-v1.5'
DIMS=384
class Embedder:
    def __init__(self):
        self.model=TextEmbedding(MODEL,cache_dir=str(BASE/'.cache/fastembed'))
        self.info=dict(model=MODEL,dims=DIMS,fastembed_version=version('fastembed'))
    def documents(self,texts):
        result=[v.tolist() for v in self.model.embed(texts)]
        if len(result)!=len(texts) or any(len(v)!=DIMS for v in result): raise ValueError('Invalid embeddings')
        return result
    def query(self,text):
        result=next(iter(self.model.query_embed(text))).tolist()
        if len(result)!=DIMS: raise ValueError('Invalid query dimension')
        return result
