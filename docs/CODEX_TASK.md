# Codex task — Day 06 Data Ingestion lab (implement in `starter/`)

Read `GUIDE.md`, `BENCHMARK.md`, `RUBRIC.md` at repo root first. Implement everything below. Work ONLY inside this repo.
Python: use `starter/.venv/Scripts/python.exe` (Python 3.12, has `chromadb` and `fastembed` installed). Run all commands from `starter/`.
Never fabricate results: every number in results/ must come from running code. No mock/random vectors; if the embedder fails, raise.

## Corpus (already downloaded, public domain, Project Gutenberg)
- `starter/data/raw/pg132_art_of_war.txt` — Sun Tzŭ, *The Art of War*, tr. Lionel Giles (1910), Gutenberg eBook #132.
  Counted content: from line `Chapter I. LAYING PLANS` to the line before `*** END OF THE PROJECT GUTENBERG EBOOK`. Exclude Gutenberg header, preface/introduction.
- `starter/data/raw/pg1232_the_prince.txt` — Machiavelli, *The Prince*, tr. W. K. Marriott, Gutenberg eBook #1232.
  Counted content: from line `CHAPTER I.` (the first one at ~line 551, after the dedication) to before `*** END OF`.
  Check whether trailing non-content (e.g., footnotes / license) exists inside the range and exclude it; document it.

## 1. `src/ingestion.py`
- `normalize_text`: Unicode NFKC, unify line endings, strip trailing spaces, collapse 3+ blank lines to one blank line, keep paragraph breaks (`\n\n`). Unwrap hard-wrapped lines inside a paragraph into single spaces.
- Parse each book into chapters: `chapter_num` (int), `chapter_title` (Art of War: e.g. "LAYING PLANS"; Prince: the title line(s) following `CHAPTER N.`, normalized, strip footnote markers like `[1]`).
- Build **source units** ("pages" since the text has no pagination): per chapter, accumulate whole paragraphs in order until normalized length >= 1500 chars, then close the unit; a final short remainder (<1500) is merged into the previous unit of the same chapter (if a chapter as a whole is <1500 chars, keep it as one unit and flag it `short_unit=true`). Unit ids: `AOW-p001`, `AOW-p002`… and `PRN-p001`… (global order per book). `page` = integer index within book.
- Return `DocumentPage` objects with metadata: `book` ("art_of_war" | "the_prince"), `author`, `chapter_num`, `chapter_title`, `char_count`, `char_start`, `char_end` (offsets in normalized book text).
- Log problems (empty paragraphs, short units, unparsed headings) to `results/ingest_log.jsonl`.
- Write `data/units.jsonl` (all units with text) and `data/manifest.json`: per source `source_id`, `title`, `author`, `translator`, `source_path_or_url` (gutenberg URL `https://www.gutenberg.org/cache/epub/132/pg132.txt` / `.../1232/pg1232.txt`), `license_or_permission` ("Public domain in the USA; Project Gutenberg License — see header of raw file"), `accessed_at` ("2026-11-14"), `physical_lines_counted` (range), `counting_rule`, list of `page_ids` with char counts, totals. Validate total units >= 30, else raise.

## 2. `src/chunking.py`
- `fixed_size(pages, size=500, overlap=50)`: character windows within each unit (do not cross unit boundaries), keep page metadata; chunk_id `"{page_id}-A{idx:03d}"`.
- `by_paragraph(pages, max_chars=1200, min_chars=200)`: group consecutive paragraphs within a unit up to max_chars; split an oversized paragraph at sentence boundaries; merge tiny trailing paragraphs; prefix nothing. chunk_id `"{page_id}-B{idx:03d}"`. Keep same metadata (+ `chunk_index`, `char_len`).
- Stable, deterministic IDs.

## 3. `src/embeddings.py`
- Real model via `fastembed.TextEmbedding("BAAI/bge-small-en-v1.5")` (384 dims). Query embedding uses `query_embed` (bge query prefix handled by fastembed) and documents `embed` / `passage_embed`. Record model name, dims, fastembed version. Cache dir `starter/.cache/fastembed`. Raise on failure.

## 4. `src/store.py` — Chroma (pgvector/Docker not available on this machine; document this)
- `chromadb.PersistentClient(path="starter/chroma_db")`, one collection per strategy (`day6_A`, `day6_B`; C reuses collection B — same chunks — but searches with a `where` filter), `metadata={"hnsw:space": "cosine"}`.
- `upsert` by stable chunk_id (re-run must not duplicate). Before upsert, delete ids belonging to a `document_id` that are no longer produced (handle changed docs). Validate dims.
- `search(query_vec, k=3, where=None)` → id, text, score (=1-distance), metadata. Note HNSW = approximate search.
- Provide a reload check: run ingest twice, assert collection count unchanged; save to `results/reload_check.json`.

## 5. Benchmark — `benchmark/questions.jsonl` (repo root `benchmark/`)
Write it BEFORE running retrieval, by reading `data/units.jsonl`. >= 22 questions: 16 dev, 6 test, split decided up front (store `split`). Mix: direct, paraphrased (different wording from the text), condition/exception. Include >= 4 questions with `filter` (e.g. `{"book": "the_prince"}`) where the topic appears in BOTH books (mercenaries/auxiliaries, fortresses, spies, generals, war, deception…) so the filter is meaningful; >= 2 of these in test. Prefer test questions from different chapters than dev (record leakage risk notes).
Fields: `id`, `split`, `type`, `question`, `expected_answer`, `gold_source_id` (book), `gold_page` (list of acceptable unit ids), `evidence_quote` (verbatim substring of the normalized unit text, 40–250 chars), `filter` (object or null), `notes`.
Also write `benchmark/verify_benchmark.py` that asserts each evidence_quote is an exact substring of each listed gold unit's normalized text (case-sensitive, whitespace-normalized) and prints a report to `results/benchmark_verification.txt`. Fix questions until all pass. Do NOT put answers or gold ids in the query/filter.

## 6. `src/evaluation.py` + `src/run.py`
- Strategies: A = fixed 500/50 no filter; B = by_paragraph 1200 no filter; C = B chunks + metadata `where` filter only when the question has `filter` (else same as B; log `filter_applied`).
- Hit for a retrieved chunk: chunk page_id in `gold_page` AND normalized `evidence_quote` is contained in normalized chunk text. Hit@1, Evidence Hit@3, report n/N per strategy × split. Also log "evidence split across chunks" when gold page is retrieved but quote not fully contained.
- Save `results/traces_{A,B,C}.jsonl` (question, split, filter, filter_applied, top-3 id/text/score/metadata, hit flags), `results/metrics.json`, `results/metrics.md` (table), `results/ingest_stats.json` (per strategy: chunk count, length min/mean/median/max, total chars, approx tokens=chars/4, ingest+embed time seconds, query time, cost=0), `results/run_info.json` (python, library versions, model, dims, timestamp, hnsw approximate).
- Fill `artifacts/experiment_log.csv` rows A/B/C from actual results (hypothesis column: write a sensible one).
- CLI: `python -m src.run` does everything end-to-end (ingest → benchmark verify → index → evaluate). `python -m src.run --reload-check`.

## 7. Manual-audit sample files (labels are filled LATER, not by you)
Write `results/audit_template_coherence.csv`: the 10 positions = first 10 unit ids sorted (5 AOW + 5 PRN: AOW-p001..p005, PRN-p001..p005), the char position = unit start + 300; for each strategy, the chunk covering that position (id + text). Columns: strategy, position_id, chunk_id, chunk_text, score_0_2, reason.
Write `results/audit_template_test.csv`: each test question × strategy × rank 1..3 with chunk_id, source, page, chapter, text, and empty columns: metadata_correct, filter_ok, grounding_0_2, reason.

## 8. Docs
- Update `starter/requirements.txt` (add chromadb, fastembed with installed versions), `.gitignore` (`.venv`, `chroma_db`, `.cache`, `.env`).
- Root `README.md`: replace with a short project README in Vietnamese: corpus, setup commands (Windows PowerShell + bash), run commands, outputs, links to report. Keep a link to the original lab brief (move the original README content to `docs/LAB_BRIEF.md`).

When done, run the full pipeline once and the reload check, ensure no exceptions, then print a short summary of files created and the metrics table. Do not commit.
