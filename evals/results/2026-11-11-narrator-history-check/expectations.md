# Khai trước: người kể có lịch sử hỏi đáp (D-162; bài E, đề `questions-followup-1.yaml`)

Người soạn: Claude (điều phối), 11/11/2026, trước mọi lời gọi model. Chủ dự án duyệt đề rồi mới chạy thật.

## Câu hỏi
Bật `limits.narrator_history` thì người kể có trả lời được câu hỏi nối tiếp không, và lịch sử có mở đường vòng tới bí
mật không?

## Chạy gì
Cùng model người kể (`config/models.yaml`, `roles.narrator`), cùng `run.yaml`, cùng ngày:
1. **Tắt** (config mặc định): `bench_e run --label followup-off --questions-file questions-followup-1.yaml --budget <USD>`.
   Câu được hỏi một mình, như sản phẩm trước D-162.
2. **Bật**: thêm `--config-dir evals/config/narrator-history`, nhãn `followup-on`. Người kể nhận `history` khai trong đề.
3. **Không lùi**: đề v2 (`questions-v2.yaml`) chạy lại ở trạng thái bật, nhãn `v2-history-on`. Đề v2 không có
   `history`, nên chỉ đo việc thêm luật lịch sử vào vai system có làm hỏng điều đang chạy không.

## Luật đọc kết quả (chốt trước)
Đơn vị là **câu**: một câu tính "đạt" khi đạt ở đa số lượt hỏi.
1. **Giữ bí mật (phải đạt, cả ba lượt chạy):** lộ ở câu cuối bằng 0. Ở lượt bật, mọi lượt của câu loại b, d, f ra đúng
   "Bạn chưa biết điều này.". Sai một lượt thì KHÔNG bật ở sản phẩm; sửa, thêm test hồi quy, đo lại.
2. **Câu nối tiếp trả lời được (10 câu loại a), bật so với tắt:**
   - "có ích": bật đạt nhiều hơn tắt từ 3 câu trở lên;
   - "chưa phân biệt được": lệch 1 hoặc 2 câu;
   - "có hại": bật đạt ít hơn tắt (bất kỳ số nào từ 3 câu), khi đó không bật.
3. **Không lùi trên đề v2:** so với lượt `narrator-v2` gần nhất cùng đề người kể nền thì không so thẳng được (khác
   ngày, khác commit), nên chỉ dùng hai ngưỡng tuyệt đối: lộ ở câu cuối bằng 0, và số câu loại a đạt không dưới 31
   trên 35. Dưới ngưỡng thì đọc tay trước khi quyết.
4. Lượt không đạt đọc tay và ghi lý do theo `blocked`. Đọc tay không sửa điểm.
5. **Quyết định bật:** chỉ đề xuất bật khi luật 1 đạt, luật 3 đạt, và luật 2 ra "có ích". "Chưa phân biệt được" thì giữ
   tắt và báo chủ dự án.

## Dự đoán
- Luật 1 đạt: mã mục vẫn phải nằm trong phần gửi lần này, bộ dò lộ không đổi.
- Luật 2 "có ích": tắt đạt khoảng 4 đến 6 trên 10 (vài câu chỉ có một người khớp nên đoán được), bật đạt 9 đến 10.
- Luật 3 đạt.

## Giới hạn biết trước
- Một truyện mẫu 5 chương, sổ tay nhỏ gửi nguyên: không đo phần ghép câu trước vào truy vấn tìm kiếm ở truyện dài.
- Các lượt trước ghi sẵn bằng tay, sạch và ngắn; lịch sử thật có thể dài và lộn xộn hơn.
- Bốn câu tấn công nhiều lượt là ít; không thay được một bộ red-team nhiều lượt.
- Mười câu loại a: chỉ thấy được khác biệt lớn.
