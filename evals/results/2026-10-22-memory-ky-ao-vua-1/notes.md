# Nhận xét đọc tay: memory-ky-ao-vua-1

Người đọc: Claude (điều phối), 22/10/2026. Đề `questions-ky-ao-vua-1.yaml`: 39 câu, chủ dự án duyệt 22/10/2026, cách chấm theo D-83. Truyện `evals/results/2026-10-21-run-ky-ao-vua-1/` (Truyện vừa, 10 chương do pipeline viết). Mỗi câu hỏi 3 lần, 6 hệ. Tổng chi phí 0,2299 USD, trần 1,00.

## Sự cố khi chạy (đã xử lý)
- Lượt đầu: hai hệ đồ thị lỗi `HARNESS_ERROR` ở 54/117 lượt mỗi hệ ("truyện bench-a-run có 0 nhân vật chính"), từ 11:48:12.
- Nguyên nhân: điều phối chạy `pytest -m graph` ở một nhánh khác đúng lúc đó. Test `test_bench_a_graph_parity.py` dùng chung id truyện `bench-a-run` trên Neo4j với lượt đo, và xoá truyện đó khi xong.
- Hai hệ đồ thị đã chạy lại vào cùng thư mục (`--systems graph,graph_quotes`). Số trong `summary.md` là của lượt chạy lại. Mục "Lỗi" vẫn liệt kê các lượt hỏng cũ vì `errors.jsonl` chỉ ghi thêm, không xoá.
- Đã sửa trong cùng commit: test dùng id riêng (`test-bench-a-*`) qua `open_graph_backend(story_id=...)` và `RunOptions.graph_story_id`, kèm test hồi quy.

## Kết quả chính
- **Trên truyện dài do pipeline viết, đồ thị đứng một mình thua rõ.**
  - Thứ hạng: nhét cả truyện 91%, RAG 84%, tóm tắt cuộn 79%, hệ lai đồ thị + câu trích 79%, đồ thị 49%, không bộ nhớ 31%.
  - Trên truyện mẫu 5 chương (đồ thị dựng tay, `2026-10-21-memory-lai-1`), hệ lai đứng đầu với 98% và đồ thị đạt 91%.
- **Nút thắt là bộ trích, không phải phần đọc đồ thị.**
  - Khi đồ thị bộ trích có đáp án (`graph_agrees: true`, 13/39 câu), hệ đồ thị đạt 97%.
  - Khi đồ thị thiếu hoặc sai (26/39 câu), hệ đồ thị chỉ đạt 24%.
  - Như vậy bộ trích chỉ dựng đúng khoảng một phần ba số sự thật mà đề hỏi. Cùng hướng với chẩn đoán của D-82: chương 2–3 có gói rỗng, KNOWS của nhân vật chính trễ 2–3 chương.
- **Khoảng cách xa:** ở câu cách từ 3 chương trở lên, đồ thị đạt 29%, hệ lai 67%, RAG 73%, nhét cả truyện 88%.
- **Hệ lai cứu được phần lớn chỗ đồ thị thiếu** (69% ở câu đồ thị thiếu hoặc sai), nhưng vẫn dưới RAG.
- **Chi phí:**
  - Nhét cả truyện tốn khoảng 5 lần mỗi câu (ngữ cảnh trung bình khoảng 59 nghìn ký tự, so với khoảng 10 nghìn ở các hệ khác), và sẽ còn tăng theo độ dài truyện.
  - RAG đạt 84% với chi phí ngang hệ đồ thị.

## Hệ quả cho sản phẩm (suy luận, chưa đo)
- Sổ tay và người kể đọc `player_view`, mà `player_view` dựng từ cùng bộ trích này. Nên ở truyện dài, sổ tay có thể thiếu điều người chơi đã đọc. Bài E chỉ đo trên truyện mẫu và truyện tu-tien-1, chưa đo trên truyện 10 chương.
- Muốn đồ thị hơn RAG ở truyện dài, phải nâng độ phủ của bộ trích trước. Đo được bằng chính đề này: tỉ lệ `graph_agrees` sau khi chạy lại bộ trích.

## Chưa kiểm
- Một lần chạy, một truyện. Khoảng tin cậy rộng (ví dụ đồ thị 40–58%).
- `graph_agrees` của 26 câu không có `derive` do người soạn khai bằng tay, code không kiểm được.
- Chưa đọc tay các câu trả lời sai của RAG và của nhét cả truyện.
