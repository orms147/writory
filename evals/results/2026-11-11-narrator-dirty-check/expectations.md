# Khai trước: người kể với câu hỏi "bẩn" (bài E, đề `questions-dirty-1.yaml`)

Người soạn: Claude (điều phối), 11/11/2026, trước mọi lời gọi model. Chủ dự án duyệt đề rồi mới chạy thật.

## Câu hỏi
Người chơi gõ không dấu, sai chính tả hay teencode, nói trống không thì người kể (`ask_narrator`, đề hiện hành theo
`limits.narrator_pages`) còn trả lời được điều đã mở khoá không, và còn giữ được bí mật không?

## Chạy gì
- Đề `evals/scenarios/narrator/questions-dirty-1.yaml`, truyện mẫu 5 chương, `plan.yaml` và `run.yaml` như đề v2.
- Model người kể theo `config/models.yaml` (`roles.narrator`), số lần hỏi mỗi câu theo `run.yaml`.
- Lệnh: `uv run python -m writory.pipeline.bench_e run --label dirty-1 --questions-file questions-dirty-1.yaml --budget <USD>`.
- Mỗi câu gốc của đề v2 được hỏi lại trong cùng lượt (`--goc`), nên so từng cặp trên cùng model, cùng đề, cùng ngày.

## Luật đọc kết quả (chốt trước)
Đơn vị là **câu gốc**: một câu tính "đạt" ở một kiểu khi đạt ở đa số lượt hỏi của kiểu đó.
1. **Giữ bí mật (phải đạt):** lộ ở câu cuối bằng 0 trên toàn đề, và mọi lượt của câu loại b ra đúng "Bạn chưa biết
   điều này.". Sai một lượt là lỗi phải sửa, thêm test hồi quy trước.
2. **Trả lời được, theo từng kiểu** (`khongdau`, `saichinhta`, `trongkhong`), so với `goc`:
   - "kém hơn": số câu gốc đạt ở kiểu đó ít hơn `goc` từ 3 câu trở lên;
   - "chưa phân biệt được": lệch 1 hoặc 2 câu;
   - "ngang": bằng nhau.
3. **Câu hai ý:** ghi số lượt đạt đủ cả hai ý, không có ngưỡng (chỉ 3 câu).
4. Lượt không đạt đọc tay và ghi lý do theo `blocked` (model tự từ chối, code chặn, thiếu cụm). Đọc tay không sửa điểm.

## Dự đoán
- Luật 1 đạt: bộ dò lộ bỏ dấu khi so chữ, và câu bí mật viết bẩn không cho model thêm thông tin.
- `khongdau`: chưa phân biệt được với `goc` (sổ tay truyện mẫu nhỏ nên gửi nguyên, model đọc được tiếng Việt không dấu).
- `saichinhta` và `trongkhong`: ngang hoặc chưa phân biệt được.

## Giới hạn biết trước
- Một truyện, sổ tay nhỏ: đề này không ép phần truy hồi. Truy hồi sổ tay bỏ dấu khi so từ (`pipeline/notebook.py`),
  còn tìm đoạn trên trang thì không bỏ dấu (`pipeline/passages.py`), nên câu không dấu có thể không kéo được đoạn văn ở
  truyện dài. Đề này không đo điều đó vì mọi câu đều có căn cứ trong sổ tay.
- Mười câu gốc, số lượt ít: chỉ thấy được khác biệt lớn.
- Chưa có câu hỏi nối tiếp nhiều lượt: người kể chưa nhận lịch sử hội thoại.
