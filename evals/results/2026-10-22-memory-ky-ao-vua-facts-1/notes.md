# Bài A trên đồ thị có Fact mới (D-93)

Đề `evals/scenarios/memory/questions-ky-ao-vua-1-facts.yaml` (dẫn xuất, chờ duyệt): cùng 39 câu của đề truyện vừa, đồ thị lấy từ `../2026-10-22-new-facts-replay-1/`. Hai hệ `graph`, `graph_quotes`, **một lần hỏi mỗi câu** (`--samples 1`), nên khoảng tin cậy rộng. Chi phí 0,0420 USD.

| | cũ (3 lần hỏi) | cũ (chỉ lần 0) | mới (1 lần) |
|---|---|---|---|
| Đồ thị, cả 39 câu | 49% | 49% (19/39) | 74% (29/39) |
| Đồ thị, 6 câu mà đồ thị mới có đáp án | 0/18 | 0/6 | 6/6 |
| Đồ thị, 7 câu còn thiếu của nhóm 13 | 6/21 | 2/7 | 2/7 |
| Đồ thị + câu trích, cả 39 câu | 79% | 79% (31/39) | 82% (32/39) |
- Đồ thị đứng một mình tăng nhiều nhất ở đúng các câu có Fact mới. Hệ lai ít đổi: nó đã lấy chi tiết từ đoạn trên trang.
- Vẫn dưới nhét cả truyện (91%) và RAG (84%) của lần đo cũ.
- `graph_agrees` của 12 câu trong đề dẫn xuất khai sau khi thấy đồ thị (xem đầu file đề), nên các dòng "Đồ thị có đáp án/thiếu" trong `summary.md` chỉ mô tả.
- Chưa kiểm: một lần hỏi; lần chạy cũ và mới khác cả bản code lẫn đề; không có hệ `rag`, `full` cho lần mới.
