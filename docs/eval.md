# Bộ đo

Mục đích và lý do chia bài: design §9, D-7. File này chứa cách làm và lệnh chạy. Con số kết quả không ghi ở đây; chúng nằm trong `evals/results/<ngày>-<tên>/`, kèm commit SHA, hash của config và tên model.

**Nguyên tắc:** khai trước câu hỏi, đáp án và cách chấm (commit vào `evals/scenarios/`) **trước khi** chạy. Không sửa câu hỏi sau khi đã thấy kết quả. Đồ thị không thắng thì ghi là không thắng.

## Bài A — Bộ nhớ
- Dữ liệu: *(chưa có)* bộ chương cố định + câu hỏi + đáp án, kèm nhóm câu hỏi và khoảng cách giữa lúc gieo và lúc hỏi.
- Nguồn đáp án đầu tiên: truyện mẫu 5 chương và đồ thị dựng tay trong `data/sample-story/` (`graph.yaml`, `answers.yaml`). Chờ chủ dự án duyệt; chưa phải bộ câu hỏi bài A.
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
- G4, prompt injection: `evals/redteam/g4_prompt_injection.yaml`. Phần `expected_wrap` chạy trong test nhanh (`tests/unit/test_safety_wrap.py`). Phần `expected_story` dành cho model thật; lệnh: *(chưa có)*.
- G5, phân loại ô tự viết: `evals/redteam/g5_classify.yaml`, mỗi câu có nhãn mong đợi. Test nhanh chỉ kiểm cấu trúc bộ câu và luồng xử lý (model giả). Đo với model thật: `cd backend && uv run python -m writory.safety.bench_g5 --out ../evals/results/<ngày>-g5` (cần `models.roles.classify`, `limits.input.custom_action_max_chars`, trần `limits.cost_usd.per_story`; chưa chạy).
