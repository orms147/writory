# Bài F: so 2 model viết trên cùng một thế giới

| Model | Tiếng Việt tự nhiên | Giọng và độ sáng tạo | Bám nhân vật và bối cảnh | Liền mạch | Nhịp và đẩy truyện | Lựa chọn có ý nghĩa | Lỗi (5 là không lỗi) | Trung bình | Hạng so sánh | USD/chương | Lỗi (code) | Lỗi lời gọi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek/deepseek-v4-flash (A) | 3 | 3 | 2 | 2 | 3 | 3 | 2 | 2.57 | 1.5 | 0.013565 | 8 | 0 |
| openai/gpt-6-luna (B) | 3 | 2 | 2 | 2 | 2 | 3 | 3 | 2.43 | 1.5 | 0.011194 | 8 | 0 |

Hạng so sánh: trung bình của hai lượt thứ tự đảo; hai lượt KHÔNG đồng ý (nghi thiên lệch vị trí).
- trình bày AB: hạng B > A
- trình bày BA: hạng A > B

Câu trích giám khảo không có thật trong truyện (G3): 1.

## Khuyến nghị đáng tiền (bước 2, điểm bước 1 đã khoá)

Khuyến nghị: openai/gpt-6-luna (B). Khuyến nghị chính: dùng B cho bản 1, không trả thêm cho A ở quy mô lớn ngay bây giờ. Cả hai đều hoàn thành 6/6 chương, không dự phòng, không cảnh bị chặn và không lỗi lời gọi, nên không có khác biệt về dừng sớm; khác biệt độ tin cậy chủ yếu là A viết lại nhiều hơn. Riêng chi phí model viết + dàn ý gần như bằng nhau, A là 0,004523 USD/chương và B là 0,004636 USD/chương, nên khoản chênh tổng chi phí nhiều khả năng đi kèm viết lại và các chi phí phụ khác; chính vì vậy không nên chỉ nhìn giá model viết thô. Cả hai đều yếu chung ở bam_nhan_vat_boi_canh 2 và lien_mach 2, tức trả thêm cho A không sửa được lỗi bám đề và liền mạch là rủi ro lớn của sản phẩm.

- deepseek/deepseek-v4-flash: chap_nhan_duoc. Chất lượng chỉ nhỉnh hơn rất ít so với B: điểm trung bình tự tính từ các tiêu chí đã khoá là 2,57 so với 2,43 của B, và xếp hạng so sánh vẫn hoà 1,5–1,5. Lợi thế nằm ở giong_sang_tao 3 so với 2 và nhip_day_truyen 3 so với 2, nhưng lại thua ở loi 2 so với 3. Đổi lại, A đắt hơn 21,2% về tổng chi phí, có 7 lượt viết lại so với 4 của B và hai bên cùng có 8 lỗi repetition theo bộ kiểm của repo. Với người chơi bình thường, lợi ích nhịp truyện của A chưa đủ bù lỗi dễ thấy và chi phí vận hành cao hơn.
- openai/gpt-6-luna: dang_tien. B chỉ kém A 0,14 điểm trung bình tự tính, vẫn hoà về xếp hạng, nhưng rẻ hơn và ổn định hơn: tổng 0,067161 USD so với 0,081388 USD, viết lại 4 so với 7, loi 3 so với 2. Điểm yếu là giong_sang_tao 2 và nhip_day_truyen 2, thấp hơn A một điểm ở cả hai tiêu chí. Đây là đánh đổi đáng tiền cho bản 1 vì chưa có bằng chứng B tệ đến mức làm mất người chơi, trong khi chi phí và độ ổn định có lợi thế rõ và đo được.

Điều chưa chắc: Một thế giới, vài chương, một giám khảo.

Giám khảo: muse (muse-wonder-1.0). Chi phí giám khảo: 0.6493 USD.

## Hai giám khảo: điểm từng giám khảo, độ đồng thuận, điểm gộp

### Điểm từng giám khảo (trung bình solo 1–5; hạng so sánh 1 là tốt nhất)

| Giám khảo | Model | Tiếng Việt tự nhiên | Giọng và độ sáng tạo | Bám nhân vật và bối cảnh | Liền mạch | Nhịp và đẩy truyện | Lựa chọn có ý nghĩa | Lỗi (5 là không lỗi) | Trung bình | Hạng so sánh |
|---|---|---|---|---|---|---|---|---|---|---|
| muse (muse-wonder-1.0) | deepseek/deepseek-v4-flash | 3.0 | 3.0 | 2.0 | 2.0 | 3.0 | 3.0 | 2.0 | 2.57 | 1.50 |
| muse (muse-wonder-1.0) | openai/gpt-6-luna | 3.0 | 2.0 | 2.0 | 2.0 | 2.0 | 3.0 | 3.0 | 2.43 | 1.50 |
| sonnet (claude-sonnet-5-5) | openai/gpt-6-luna | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.00 | 1.00 |
| sonnet (claude-sonnet-5-5) | deepseek/deepseek-v4-flash | 3.0 | 3.0 | 3.0 | 2.0 | 3.0 | 3.0 | 2.0 | 2.71 | 2.00 |

### Độ đồng thuận

- Các giám khảo xếp các model cùng thứ tự theo điểm trung bình solo: KHÔNG.
- Các giám khảo xếp các model cùng thứ tự theo hạng so sánh: KHÔNG.
- Chênh điểm từng mục: chênh tuyệt đối trung bình và lớn nhất giữa các giám khảo, trên các model; "cùng chiều" là tỉ lệ cặp model mà các giám khảo nói cùng bên hơn (hoà tính nửa).

| Tiêu chí | Chênh TB | Chênh lớn nhất | Cùng chiều |
|---|---|---|---|
| Tiếng Việt tự nhiên | 0.00 | 0.0 | 0.50 |
| Giọng và độ sáng tạo | 0.50 | 1.0 | 0.50 |
| Bám nhân vật và bối cảnh | 1.00 | 1.0 | 0.50 |
| Liền mạch | 0.50 | 1.0 | 0.50 |
| Nhịp và đẩy truyện | 0.50 | 1.0 | 0.50 |
| Lựa chọn có ý nghĩa | 0.00 | 0.0 | 0.50 |
| Lỗi (5 là không lỗi) | 0.00 | 0.0 | 1.00 |

### Điểm gộp

Cách gộp: điểm gộp của một model là trung bình cộng điểm trung bình solo của các giám khảo, trọng số bằng nhau; hạng gộp là trung bình cộng hạng so sánh. Không chuẩn hoá thang riêng của từng giám khảo, nên giám khảo khắt khe hơn kéo điểm gộp xuống. Hai giám khảo không có đa số: chênh lớn giữa họ cần đọc tay, không dựa vào điểm gộp.

| Model | Điểm gộp | Hạng gộp |
|---|---|---|
| openai/gpt-6-luna | 2.71 | 1.25 |
| deepseek/deepseek-v4-flash | 2.64 | 1.75 |

### Khuyến nghị đáng tiền theo từng giám khảo (bước 2)

- muse: openai/gpt-6-luna
- sonnet: openai/gpt-6-luna
