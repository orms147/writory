# Nhận xét đọc tay: memory-lai-1

Người đọc: Claude (điều phối), 21/10/2026. Chỉ chạy hệ `graph_quotes` (D-81): đồ thị cộng 2 đoạn BM25 trên chữ các chương cũ, cộng chương N. Cùng đề và cùng model với `2026-10-21-memory-lan-1`. Chi phí 0,0183 USD.

- **Đúng 98% (130/132), CI 95% là 95–100%.** So với lan-1: nhét cả truyện 92% (86–95), đồ thị 91%, RAG BM25 91%. Cận dưới của hệ lai chạm cận trên của nhét cả truyện, nên hệ lai hơn, nhưng mới đo trên một truyện 5 chương, mỗi câu 3 lần.
- Hai loại lỗi của hệ đồ thị thuần đều được sửa:
  - nhóm quan hệ đạt 100% (27/27), trước đó đồ thị 81%; câu phủ định "có phải họ hàng" giờ đúng;
  - chi tiết gắn với nguồn lời kể (`alive-07`) cũng đúng.
- Ngữ cảnh trung bình 6283 ký tự, ít hơn nhét cả truyện (7162). Trên truyện dài, khoảng chênh này phải lớn dần vì ngữ cảnh hệ lai gần như không phình theo số chương. Đây là điều cần đo tiếp trên truyện dài.
- Kết luận cho dự án: trên truyện ngắn, **đồ thị cộng truy hồi chữ** là cách tốt nhất; đồ thị đứng một mình thì không.
