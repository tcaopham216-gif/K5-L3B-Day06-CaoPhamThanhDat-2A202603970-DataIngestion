# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline
- Chủ đề, nguồn/quyền, số trang và quy tắc tính trang: Sun Tzu, The Art of War (Lionel Giles), Gutenberg #132; Machiavelli, The Prince (W. K. Marriott), #1232. Public domain tại Hoa Kỳ; xem giấy phép Gutenberg trong nguồn. starter/data/manifest.json ghi tương ứng 117 và 87 trang logic, không phải trang in. Gom nguyên đoạn đến ít nhất 1500 ký tự; phần cuối ngắn ghép trong cùng chương, chương ngắn vẫn giữ và gắn cờ. Loại lời mở đầu, giấy phép và phụ lục Valentino/Castruccio.
- Chuẩn hóa, lỗi và giới hạn: tiêu đề chương thành metadata, giữ ranh giới đoạn và chú giải. Offsets là khoảng ký tự Unicode nửa mở trong văn bản chuẩn hóa. Không nối xuyên chương. starter/results/ingest_log.jsonl ghi các đoạn rỗng, có thể là dòng phân cách chứ không phải mất nội dung. Chú giải dài có thể lấn át văn bản chính.
- Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí: BAAI/bge-small-en-v1.5 chạy local qua fastembed 0.9.1, 384 chiều; Chroma 1.5.9, cosine HNSW approximate. Không có Docker/pgvector nên dùng Chroma thay pgvector. Từ starter chạy `python -m src.run` và `python -m src.run --reload-check` bằng Python venv đã cài dependencies. Orchestrator đã chạy thành công với venv đường dẫn ngắn. starter/.venv gặp Windows MAX_PATH: “DLL load failed while importing cygrpc: The filename or extension is too long”. Nên clone vào đường dẫn ngắn như C:\d6 và dùng venv ngắn. Chi phí dịch vụ 0, chưa định giá điện/phần cứng/công sức. reload_check.json passed=true, số chunk trước/sau A=990, B=476.
- Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn: source, document_id, page/page_id, book, chapter_num/chapter_title và offsets lấy từ nguồn, manifest và vị trí chuỗi chuẩn hóa. book dùng giới hạn tác phẩm theo ngữ cảnh người dùng. Giá trị filter có sẵn trong câu hỏi, không suy từ gold khi truy xuất.

## Cấu hình và benchmark
- A / B / C (tham số cụ thể, khác biệt duy nhất B–C): A cửa sổ 500 ký tự, overlap 50. B gom đoạn theo câu, mục tiêu tối đa 1200 ký tự; phần cuối dưới 200 ghép lùi. Giới hạn mềm vì giữ câu quá dài và ghép phần cuối. C dùng nguyên chunks/index/embedding của B, chỉ thêm filter book khi câu hỏi cung cấp. A–B đổi chunking; B–C là filter only.
- ≥20 câu: phân chia ≥15 dev / ≥5 test, câu metadata filter và cách kiểm chứng evidence: benchmark/questions.jsonl có 22 câu, 16 dev, 6 test. Filter tại q02, q16, q20, q21, gồm 2 câu test. Chương test tách dev nhưng vẫn chung tác giả/chủ đề/bản dịch. benchmark_verification.txt xác nhận toàn bộ 22 câu có quote đúng nguồn. Hit yêu cầu đúng gold page và chứa đầy đủ quote sau chuẩn hóa khoảng trắng, phân biệt hoa thường; đúng trang chưa đủ.
- Tiêu chí chọn chiến lược đã chốt trước khi xem test: Evidence Hit@3 dev, rồi Hit@1 dev, rồi tài nguyên. Không đổi lựa chọn theo test. Dev Hit@3 hòa A=B=C 8/16; Hit@1 B=C 7/16 cao hơn A 5/16, nên chọn B (C tương đương về kết quả truy xuất). B là cấu hình cơ sở không cần scope.

## Kết quả
| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| A | dev | 5/16 | 8/16 | 990 | ingest+embed 80.91 s | 0 |
| A | test | 3/6 | 5/6 | 990 | cùng lượt build A | 0 |
| B | dev | 7/16 | 8/16 | 476 | ingest+embed 73.19 s | 0 |
| B | test | 4/6 | 4/6 | 476 | cùng lượt build B | 0 |
| C | dev | 7/16 | 8/16 | 476 (chung B) | build bổ sung 0 s | 0 |
| C | test | 4/6 | 4/6 | 476 (chung B) | chung index B | 0 |

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | 0.5 (10) | 18/18 | 2/2 (đúng scope, không áp filter) | 1/0/5; 1.67 |
| B | 1.6 (10) | 18/18 | 2/2 (đúng scope, không áp filter) | 0/2/4; 1.67 |
| C | 1.6 (10) | 18/18 | 2/2 (áp filter) | 0/2/4; 1.67 |

Đường dẫn trace, nhãn thủ công và cách chọn mẫu:

- Trace: [A](../../starter/results/traces_A.jsonl), [B](../../starter/results/traces_B.jsonl), [C](../../starter/results/traces_C.jsonl). Số liệu: [metrics.json](../../starter/results/metrics.json), [metrics.md](../../starter/results/metrics.md), [ingest_stats.json](../../starter/results/ingest_stats.json), [run_info.json](../../starter/results/run_info.json).
- Nhãn theo rubric thủ công, người gán thực tế là AI: [audit_labels_coherence.csv](../../starter/results/audit_labels_coherence.csv), [audit_labels_test.csv](../../starter/results/audit_labels_test.csv). Coherence lấy @300 tại AOW-p001 đến AOW-p005 và PRN-p001 đến PRN-p005, chọn chunk đầu tiên theo thứ tự xác định khi overlap. Đây là mẫu cố định đầu corpus, không phải mẫu ngẫu nhiên.
- Audit test lấy mọi câu test và top-three mỗi chiến lược. Metadata tính theo chunk; filter theo câu test có scope; grounding theo toàn bộ bằng chứng của từng câu, không cộng lặp nhãn ở từng rank. Điểm trung bình trong bảng tính trực tiếp từ hai CSV nhãn. A/B đạt scope 2/2 tự nhiên, không có nghĩa đã áp bộ lọc.

## Phân tích và kết luận
- So sánh A–B và B–C; 2 ví dụ sai có ID câu và nguồn: A–B giữ model/store/benchmark, đổi chunking. B tăng Hit@1 dev và coherence từ 0.5 lên 1.6, nhưng Hit@3 dev vẫn 8/16. Test A Hit@3 5/6 cao hơn B 4/6; B Hit@1 4/6 so với A 3/6. Test chỉ 6 câu nên chịu biến động mẫu nhỏ; không kết luận B tốt hơn trên mọi thước đo.
  - q18, gold AOW-p106, nguồn pg132_art_of_war.txt: B/C lấy AOW-p014-B001, AOW-p006-B001, AOW-p106-B002. Các đoạn đầu nói sai lầm khi điều quân và chiến tranh kéo dài; đoạn đúng trang nói cơn giận có thể đổi thành vui và sự thận trọng, thiếu quote cấm đưa quân chỉ để thỏa giận. Evidence Hit@3=false dù có gold page. A cũng sai, lấy AOW-p014-A002, AOW-p006-A001, AOW-p009-A004, không có gold page.
  - q21, gold PRN-p072, nguồn pg1232_the_prince.txt: B/C lấy PRN-p015-B002, PRN-p062-B001, PRN-p072-B001. Các đoạn nói năng lực người cai trị, thể chế và hoàn cảnh xây pháo đài; đoạn đúng trang kết thúc trước bằng chứng “pháo đài tốt nhất là không bị dân ghét”. B/C không đạt Hit@3. A lấy PRN-p072-A003 đầu tiên và chứa đủ quote nên đạt. Cờ evidence_split_across_chunks chỉ chẩn đoán đúng trang nhưng thiếu quote, không tự chứng minh lỗi do cắt tại biên.
- Chiến lược chọn, đánh đổi, điều kiện áp dụng: chọn B theo quy tắc dev. A có 990 chunks, B có 476; embed+index tương ứng 80.71 s và 73.00 s. B ít chunks hơn, coherence tốt hơn trên mẫu audit, phù hợp văn xuôi theo đoạn; context dài vẫn có thể làm giảm tập trung và không bảo đảm đủ bằng chứng. C không build lại index. B–C có cùng thứ tự chunk và cùng hit trên mọi câu. Cả 4 câu filter, B chưa lọc đã chỉ trả đúng book. Benchmark filter chưa đủ khả năng phân biệt tác dụng của bộ lọc; không có bằng chứng filter giúp tăng chất lượng lần chạy này.
- Hạn chế của dữ liệu, nhãn, test nhỏ, đo thời gian/chi phí: corpus hẹp, chú giải dài, chủ đề trùng; nhãn AI và mẫu coherence tập trung đầu corpus gây bias. Grounding đều 1.67 nhưng phân bố khác; chỉ số truy xuất không đánh giá câu trả lời LLM. Search toàn benchmark A=0.59 s, B=0.58 s, C=0.78 s; chưa gồm query embedding chung 0.72 s và model load 5.75 s. Đây là số đo của lượt chạy, không phải bảo đảm latency. HNSW xấp xỉ; chi phí 0 là phí dịch vụ local ghi nhận.
- Nếu làm lại hoặc mở rộng, cải tiến gì? Tạo câu đa nghĩa mà tìm kiếm không lọc thực sự trả nhầm sách, vẫn lấy scope từ người dùng; đóng băng benchmark trước chạy. Mở rộng corpus/test độc lập, nhờ người rà soát nhãn mù chiến lược. Kiểm tra các đoạn thiếu quote, thử truy xuất đoạn lân cận và chọn theo dev trước khi đánh giá test mới.
