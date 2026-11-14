"""Character windows and paragraph/sentence chunks with source offsets."""
import re
from .models import Chunk

def make(page, label, idx, start, end):
    text=page.text[start:end]
    meta={**page.metadata,'chunk_index':idx,'char_len':len(text),'chunk_char_start':start,'chunk_char_end':end}
    return Chunk(f"{meta['page_id']}-{label}{idx:03d}",page.document_id,page.source,page.page,text,meta)

def fixed_size(pages,size=500,overlap=50):
    if not 0<=overlap<size: raise ValueError('Require 0 <= overlap < size')
    out=[]
    for p in pages:
        start=0;idx=1
        while start<len(p.text):
            end=min(start+size,len(p.text));out.append(make(p,'A',idx,start,end))
            if end==len(p.text): break
            start+=size-overlap;idx+=1
    return out

def by_paragraph(pages,max_chars=1200,min_chars=200):
    if not 0<min_chars<=max_chars: raise ValueError('Invalid size limits')
    out=[]
    for p in pages:
        pieces=[]
        for m in re.finditer(r'[^\n]+',p.text):
            if len(m[0])<=max_chars: pieces.append((m.start(),m.end()));continue
            # A single sentence exceeding max_chars stays whole: preserve meaning.
            start=m.start()
            for s in re.finditer(r'.+?(?:[.!?](?=\s|$)|$)',m[0]):
                a=m.start()+s.start();b=m.start()+s.end()
                while a<b and p.text[a].isspace(): a+=1
                if b>a: pieces.append((a,b))
        groups=[]
        for a,b in pieces:
            if groups and b-groups[-1][0]<=max_chars: groups[-1][1]=b
            else: groups.append([a,b])
        if len(groups)>1 and groups[-1][1]-groups[-1][0]<min_chars:
            # Explicit trailing-minimum exception to the soft max bound.
            groups[-2][1]=groups[-1][1];groups.pop()
        out.extend(make(p,'B',i,a,b) for i,(a,b) in enumerate(groups,1))
    return out
