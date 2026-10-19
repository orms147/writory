# Bộ đo

Mục đích và lý do chia bài: design §9, D-7. File này chứa cách làm và lệnh chạy. Con số kết quả không ghi ở đây; chúng nằm trong `evals/results/<ngày>-<tên>/`, kèm commit SHA, hash của config và tên model.

**Nguyên tắc:** khai trước câu hỏi, đáp án và cách chấm (commit vào `evals/scenarios/`) **trước khi** chạy. Không sửa câu hỏi sau khi đã thấy kết quả. Đồ thị không thắng thì ghi là không thắng.

## Bài A — Bộ nhớ
- Dữ liệu: *(chưa có)* bộ chương cố định + câu hỏi + đáp án, kèm nhóm câu hỏi và khoảng cách giữa lúc gieo và lúc hỏi.
- Đối thủ bản 1: tóm tắt cuộn, nhét cả truyện, đồ thị.
- Chỉ số: độ đúng theo nhóm và theo khoảng cách, kèm `n` và khoảng tin cậy; token vào; chi phí.
- Lệnh: *(chưa có)*

## Bài B — Người canh
- Dữ liệu: cảnh sạch + cảnh đã cài lỗi, có nhãn loại lỗi.
- Chỉ số: recall theo loại lỗi; tỉ lệ báo nhầm trên cảnh sạch.
- Lệnh: *(chưa có)*

## Bài C — Trích thực thể (bản 2)
- Dữ liệu: câu tiếng Việt khó (trùng họ, biệt danh, đổi tên, xưng hô đổi theo quan hệ).
- Chỉ số: độ chính xác và độ phủ khi gộp/tách thực thể.

## Bài D — Chất lượng văn theo model
- Dữ liệu: 3 dàn ý cảnh mẫu, thang chấm khai trước.
- Người chấm là chính; LLM chấm so cặp (khác họ model với model viết, ≥ 3 lần) chỉ để sàng lọc.
- Kết quả cập nhật danh sách model trong `config/models.yaml`.
- Lệnh: *(chưa có)*

## Red-team guardrail
- Dữ liệu: `evals/redteam/`. Mỗi câu có kết quả mong đợi: bị chặn / không lộ / đúng schema.
- Với model giả thì chạy trong test nhanh. Với model thật thì chạy riêng, có trần chi phí.
