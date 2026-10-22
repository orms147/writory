# Bài F: so 2 model viết trên cùng một thế giới

| Model | Tiếng Việt tự nhiên | Giọng và độ sáng tạo | Bám nhân vật và bối cảnh | Liền mạch | Nhịp và đẩy truyện | Lựa chọn có ý nghĩa | Lỗi (5 là không lỗi) | Trung bình | Hạng so sánh | USD/chương | Lỗi (code) | Lỗi lời gọi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| openai/gpt-6-luna (B) | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3.00 | 1.0 | 0.011194 | 8 | 0 |
| deepseek/deepseek-v4-flash (A) | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.71 | 2.0 | 0.013565 | 8 | 0 |

Hạng so sánh: trung bình của hai lượt thứ tự đảo; hai lượt đồng ý.
- trình bày AB: hạng B > A
- trình bày BA: hạng B > A

Câu trích giám khảo không có thật trong truyện (G3): 3.

## Khuyến nghị đáng tiền (bước 2, điểm bước 1 đã khoá)

Khuyến nghị: openai/gpt-6-luna (B). B thắng cả hai chiều: chất lượng không thấp hơn ở tiêu chí nào và cao hơn ở liền mạch cùng lỗi, trong khi chi phí thấp hơn và độ tin cậy tốt hơn (viết lại 4 so với 7). Cả hai đều chạy đủ 6/6 chương, không dừng sớm, không lỗi gọi, không cảnh bị chặn, nên chênh lệch độ tin cậy chủ yếu nằm ở số lần viết lại. Chênh chi phí tuyệt đối rất nhỏ (khoảng 0,0024 USD/chương), nên quyết định dựa chủ yếu vào chất lượng, và ở đó B vượt trội. Không có lý do để trả thêm cho A.

- deepseek/deepseek-v4-flash: khong_dang_tien. Tốn hơn (0,0136 so với 0,0112 USD/chương, tổng 0,081 so với 0,067 USD) và phải viết lại nhiều hơn (7 so với 4 lần), nhưng điểm lại thấp hơn ở hai tiêu chí: liền mạch 2 so với 3, lỗi 2 so với 3. Hạng trung bình 2,0. Các tiêu chí còn lại bằng B. Trả thêm tiền mà chất lượng thấp hơn nên không đáng.
- openai/gpt-6-luna: dang_tien. Rẻ hơn khoảng 17% mỗi chương, ít phải viết lại hơn, hạng 1,0 và hơn A ở liền mạch và lỗi. Chi phí riêng model viết gần như ngang nhau (0,004636 so với 0,004523 USD/chương), nên phần chênh nằm ở các lần viết lại, và B tiết kiệm đúng chỗ đó. Điểm trung bình vẫn chỉ mức 3 nên chưa xuất sắc, nhưng là lựa chọn tốt hơn cả về tiền lẫn chất lượng.

Điều chưa chắc: Chỉ một thế giới, một đề bài và 6 chương, nên chưa thể kết luận model nào ổn định hơn khi chơi dài hay ở thể loại khác.; Chỉ một giám khảo chấm, điểm nguyên mức 2–3 nên chênh lệch giữa hai truyện nhỏ và có thể do nhiễu chấm.; Số lần viết lại (7 so với 4) chỉ là một mẫu; chạy lại có thể cho số khác, nên không nên coi B ổn định hơn một cách chắc chắn.; Bộ kiểm văn của repo báo cùng 8 lỗi lặp ở cả hai, nên không phân biệt được độ tin cậy theo tiêu chí đó.; Chênh chi phí chỉ vài phần trăm xu mỗi chương; nếu nhiều người chơi nhiều chương thì mới đáng kể, còn với bản 1 quy mô nhỏ thì chất lượng quan trọng hơn.; Cả hai đều chỉ đạt mức trung bình (3/5) ở hầu hết tiêu chí, nên bản 1 cần chấp nhận chất lượng vừa phải hoặc thử thêm model khác nếu muốn cao hơn.

Chi phí giám khảo: 0.4921 USD.
