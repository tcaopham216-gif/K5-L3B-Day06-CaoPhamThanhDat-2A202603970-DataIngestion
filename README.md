# Day 06 — Nạp dữ liệu và truy xuất bằng chứng

Corpus gồm *The Art of War* (Sun Tzu, bản dịch Lionel Giles) và *The Prince* (Machiavelli, bản dịch W. K. Marriott), từ Project Gutenberg, public domain tại Hoa Kỳ. Nội dung gốc nằm trong starter/data/raw. Chỉ đếm các chương; loại lời mở đầu, giấy phép và hai tác phẩm phụ lục sau chương XXVI của The Prince. Manifest ghi ranh giới dòng và đơn vị nguồn.

Cài đặt trong Windows PowerShell, từ thư mục gốc:

```powershell
cd starter
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --default-timeout=120 -r requirements.txt
.\.venv\Scripts\python.exe -m src.run
.\.venv\Scripts\python.exe -m src.run --reload-check
```

Bash (Linux/macOS; thay đường dẫn Python theo môi trường):

```bash
cd starter
python3.12 -m venv .venv
.venv/bin/python -m pip install --default-timeout=120 -r requirements.txt
.venv/bin/python -m src.run
.venv/bin/python -m src.run --reload-check
```

Pipeline đã chạy thành công bởi orchestrator bằng venv đường dẫn ngắn. Trên Windows, nên clone vào đường dẫn ngắn như C:\d6 và giữ đường dẫn venv ngắn. starter/.venv ở đường dẫn repo dài đã gặp Windows MAX_PATH khi import grpc: “DLL load failed while importing cygrpc: The filename or extension is too long”. Các lệnh bên trên dùng được khi repo/venv ở đường dẫn ngắn; nếu venv ở nơi khác, thay đường dẫn Python tương ứng. Không chạy đồng thời hai tiến trình cài pip. Lần đầu tải model BAAI/bge-small-en-v1.5 (384 chiều) vào starter/.cache/fastembed. Model chạy local, chi phí dịch vụ bằng 0; lỗi model sẽ dừng pipeline. Chroma lưu trong starter/chroma_db, cosine HNSW là tìm kiếm xấp xỉ. Máy không có pgvector/Docker, nên dùng Chroma.

A: cửa sổ 500 ký tự, overlap 50. B: nhóm đoạn khoảng 1200 ký tự. C: dùng chung index B, chỉ thêm filter book được cung cấp trong câu hỏi. Câu quá dài được giữ nguyên; nhóm cuối dưới 200 ký tự được ghép vào nhóm trước, nên giới hạn 1200 là giới hạn mềm trong hai trường hợp này. Mỗi chunk có source, document_id, page, book, chapter và offsets để truy vết.

Benchmark cố định ở [benchmark/questions.jsonl](benchmark/questions.jsonl): 16 dev, 6 test, 4 câu filter (2 test). Test dùng chương khác dev nhưng vẫn có rủi ro trùng chủ đề/tác giả. Chọn theo Evidence Hit@3 trên dev, sau đó Hit@1 và tài nguyên; không tinh chỉnh theo test. Chỉ số đo bằng chứng truy xuất, không phải độ chính xác trả lời LLM.

Đầu ra: starter/data/units.jsonl, manifest.json; starter/results chứa log ingest, xác minh benchmark, traces A/B/C, metrics, thống kê, run_info, reload_check và hai CSV nhãn audit. Nhãn audit nằm trong starter/results/audit_labels_coherence.csv và audit_labels_test.csv. Labeler là AI: Claude Code điều phối OpenAI Codex CLI hỗ trợ code, benchmark và nhãn audit; sinh viên phải rà soát nhãn, có rủi ro bias. Pipeline và reload check đã chạy thành công. CLI cập nhật artifacts/experiment_log.csv từ kết quả thật và ghim phiên bản chromadb/fastembed sau khi chạy thành công.

[Báo cáo cá nhân cuối cùng](report/individual/MSSV_HoTen.md) · [Rubric](RUBRIC.md)

Kết quả: dev Hit@3 hòa 8/16, Hit@1 B/C 7/16 so với A 5/16 nên chọn B theo quy tắc dev. Test Hit@3 A 5/6, B/C 4/6; mẫu nhỏ nên không khẳng định B luôn tốt hơn. C có cùng kết quả với B trên mọi câu: B chưa lọc đã trả đúng sách ở cả 4 câu filter, nên benchmark chưa chứng minh lợi ích bộ lọc. Coherence A 0.5, B/C 1.6; grounding đều 1.67 theo audit AI.
