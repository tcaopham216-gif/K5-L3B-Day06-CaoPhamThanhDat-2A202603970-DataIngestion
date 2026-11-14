"""Deterministic Gutenberg chapter and source-unit ingestion."""
import json
import re
import unicodedata
from dataclasses import asdict
from pathlib import Path
from .models import DocumentPage

BASE = Path(__file__).resolve().parents[1]
SOURCES = [
    ('AOW', 'art_of_war', 'The Art of War', 'Sun Tzu', 'Lionel Giles (1910)', '132', 'pg132_art_of_war.txt'),
    ('PRN', 'the_prince', 'The Prince', 'Niccolo Machiavelli', 'W. K. Marriott', '1232', 'pg1232_the_prince.txt'),
]

def normalize_text(text):
    text = unicodedata.normalize('NFKC', text).replace('\r\n', '\n').replace('\r', '\n')
    text = '\n'.join(line.rstrip() for line in text.split('\n'))
    return '\n\n'.join(' '.join(p.split()) for p in re.split(r'\n[ \t]*\n+', text) if p.strip())

def roman(s):
    vals = dict(I=1,V=5,X=10,L=50,C=100,D=500,M=1000)
    return sum(-vals[c] if i+1 < len(s) and vals[c] < vals[s[i+1]] else vals[c] for i,c in enumerate(s))

def ingest():
    (BASE/'results').mkdir(exist_ok=True)
    logs, pages, manifest = [], [], []
    for prefix, book, title, author, translator, ebook, filename in SOURCES:
        lines = (BASE/'data/raw'/filename).read_text(encoding='utf-8-sig').splitlines()
        start = next(i for i,l in enumerate(lines) if l.startswith('Chapter I. LAYING PLANS' if prefix=='AOW' else 'CHAPTER I.'))
        end_marker = next(i for i,l in enumerate(lines) if l.startswith('*** END OF'))
        end = next((i for i in range(start,end_marker) if lines[i].startswith('DESCRIPTION OF THE METHODS ADOPTED')), end_marker)
        heading = re.compile(r'^(?:Chapter|CHAPTER) ([IVXLCDM]+)\.(.*)$')
        heads = [(i,heading.match(lines[i])) for i in range(start,end) if heading.match(lines[i])]
        assert len(heads) == (13 if prefix=='AOW' else 26)
        for i in range(start,end):
            if lines[i].startswith(('Chapter ', 'CHAPTER ')) and not heading.match(lines[i]):
                logs.append(dict(problem='unparsed_heading',book=book,line=i+1,text=lines[i]))
        book_text, book_pages = '', []
        for h,(idx,m) in enumerate(heads):
            stop = heads[h+1][0] if h+1 < len(heads) else end
            body_start = idx+1
            if prefix=='AOW': chapter_title = normalize_text(m[2])
            else:
                while body_start<stop and not lines[body_start].strip(): body_start+=1
                title_lines=[]
                while body_start<stop and lines[body_start].strip():
                    title_lines.append(lines[body_start]); body_start+=1
                chapter_title=normalize_text(re.sub(r'\[\d+\]', '', '\n'.join(title_lines)))
            raw='\n'.join(lines[body_start:stop])
            # Blank separator runs are not paragraphs. Log extra empty slots explicitly.
            for empty in re.finditer(r'\n(?:[ \t]*\n){2,}', raw):
                logs.append(dict(problem='empty_paragraph', book=book, chapter_num=roman(m[1]), raw_offset=empty.start()))
            body=normalize_text(raw)
            if book_text: book_text+='\n\n'
            offset=len(book_text); book_text+=body
            paras=list(re.finditer(r'[^\n]+(?:\n(?!\n)[^\n]+)*',body))
            groups=[]; begin=0
            for p in paras:
                if p.end()-begin>=1500:
                    groups.append([begin,p.end()]); begin=p.end()+2
            if begin<len(body):
                if groups: groups[-1][1]=len(body)
                else: groups.append([0,len(body)])
            for a,b in groups:
                page=len(book_pages)+1; pid=f'{prefix}-p{page:03d}'; text=body[a:b]
                meta=dict(page_id=pid,book=book,author=author,chapter_num=roman(m[1]),chapter_title=chapter_title,char_count=len(text),char_start=offset+a,char_end=offset+b,short_unit=len(text)<1500)
                obj=DocumentPage(book,filename,page,text,meta)
                pages.append(obj);book_pages.append(obj)
                if meta['short_unit']: logs.append(dict(problem='short_unit',page_id=pid,char_count=len(text)))
        for p in book_pages: assert book_text[p.metadata['char_start']:p.metadata['char_end']]==p.text
        (BASE/'data'/f'{book}.normalized.txt').write_text(book_text,encoding='utf-8')
        manifest.append(dict(source_id=book,title=title,author=author,translator=translator,source_path_or_url=f'https://www.gutenberg.org/cache/epub/{ebook}/pg{ebook}.txt',license_or_permission='Public domain in the USA; Project Gutenberg License — see header of raw file',accessed_at='2026-11-14',physical_lines_counted=dict(start=start+1,end=end),counting_rule='Inclusive 1-based raw lines; chapter headings retained as metadata, chapter prose and inline notes counted. Whole normalized paragraphs accumulated to >=1500 chars, final short remainder merged within chapter. Offsets are half-open in saved normalized book text.',excluded_trailing=dict(start=end+1,end=end_marker,reason='Appended Valentino narrative and Life of Castruccio Castracani, not chapters of The Prince') if end<end_marker else None,page_ids=[dict(page_id=p.metadata['page_id'],char_count=len(p.text)) for p in book_pages],total_units=len(book_pages),total_chars=sum(len(p.text) for p in book_pages)))
    assert len(pages)>=30
    (BASE/'data/units.jsonl').write_text(''.join(json.dumps(dict(**asdict(p),page_id=p.metadata['page_id']),ensure_ascii=False)+'\n' for p in pages),encoding='utf-8')
    (BASE/'data/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (BASE/'results/ingest_log.jsonl').write_text(''.join(json.dumps(l,ensure_ascii=False)+'\n' for l in logs),encoding='utf-8')
    return pages
