# Nhận xét đọc tay: memory-lan-1

Người đọc: Claude (điều phối), 21/10/2026. Nguồn: `summary.md`, `results.jsonl`.

Lần đo thật đầu tiên của bài A. Truyện mẫu 5 chương, đề 44 câu × 3 lần, GPT-6 Luna (suy luận low) trả lời cho cả 5 hệ. Tổng chi phí 0,0737 USD.

## Kết luận
- Độ chính xác: **nhét cả truyện 92%**, **đồ thị 91%**, **RAG BM25 91%**, tóm tắt cuộn 86%, không bộ nhớ 59%. Ba hệ đầu nằm trong cùng khoảng tin cậy, nên **trên truyện 5 chương, đồ thị không hơn RAG hay nhét cả truyện**.
- Điều này đúng như dự đoán ở design §9. Truyện ngắn nằm gọn trong context, nên "nhét cả truyện" là mốc khó vượt. Lợi thế của đồ thị (context cố định, không phình theo truyện) chỉ đo được trên truyện dài.
- Ngữ cảnh trung bình mỗi câu: đồ thị 5121 ký tự, nhét cả truyện 7162 ký tự. Truyện mẫu chỉ có 5 chương nên chênh ít.
- Không bộ nhớ sập theo khoảng cách (31% ở câu cách 1–2 chương, 23% ở câu cách 3 chương trở lên). Đồ thị giữ đều (83%, 93%). Như vậy bộ đề có phân biệt được hệ có nhớ và hệ không nhớ.
- Câu suy luận (`knows-06`, `inference`): cả 5 hệ đều đúng 3/3, kể cả "không bộ nhớ". Vậy chữ của chương 5 đã đủ để suy ra; câu này không thổi phồng hệ đồ thị.

## Hệ đồ thị sai ở đâu (12/132 lượt)
1. **Chi tiết nhỏ chỉ có trong chữ:** `alive-07` ("Lão Gù bị đánh vào chỗ nào?") và `item-10` (ai giữ xấp thư). Đồ thị không lưu chi tiết này nên đồ thị trả "Không biết", trong khi các hệ đọc chữ trả đúng.
2. **Điều phủ định:** `rel-08`, `rel-09` ("Cai Trần Văn Khải có phải họ hàng của Minh?"). Đồ thị không có cạnh "không họ hàng", nên model đoán "Có" từ chuyện cùng họ Trần. Các hệ đọc chữ thấy câu phủ định trên trang.
3. **Ai biết lời nói dối:** `lie-06`, `lie-07`. Đồ thị trả "Không". Cần đọc ngữ cảnh đồ thị thật trong `results.jsonl` để biết là đồ thị dựng tay thiếu cạnh `KNOWS` hay là phần đọc đồ thị không đưa cạnh đó vào ngữ cảnh. Chưa kiểm.

## Việc tiếp
- Thử **hệ lai**: đồ thị cộng các câu trích trên trang mà đồ thị đã lưu, hoặc đồ thị cộng BM25. Hai loại lỗi 1 và 2 đều là chỗ đọc chữ mạnh hơn.
- Đo bài A trên **truyện dài do pipeline viết** (Truyện vừa, 10–20 chương), nơi "nhét cả truyện" tốn và loãng dần. Ở đó mới trả lời được câu hỏi lõi của dự án.
