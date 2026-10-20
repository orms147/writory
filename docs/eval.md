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
Cách chấm: D-25. Vị trí code, dữ liệu, kết quả: D-24. Code: `writory.quality.bench_d`.

- **Dữ liệu** (`evals/scenarios/quality/`, khoá sau khi chạy; muốn sửa thì tăng `version`):
  - `cases.yaml`: dàn ý cảnh, gồm thể loại, ngôi kể, giọng, chuyện trước, nhân vật, bảng xưng hô, các nhịp, bí mật không được lộ, độ dài. `focus` và `tags` chỉ để phân tích, không vào prompt.
  - `rubric.yaml`: lời dặn giám khảo và các tiêu chí, gồm thang 1–5 có mô tả neo, hoặc nhị phân. Bắt buộc có tiêu chí nhị phân `giu_bi_mat`.
  - `models.yaml`: model viết (id OpenRouter, giá để ước tính trước, `reasoning`) và giám khảo. Model họ `anthropic/` bị từ chối vì cùng họ với giám khảo.
  - `style_guide_vi.md`: system prompt của model viết. Chú thích HTML ở đầu file bị bỏ trước khi gửi.
- **Viết:** gọi qua `OpenRouterClient`. System là hướng dẫn văn phong; user là đề bài dựng từ case (mẫu `BRIEF_TEMPLATE_VERSION`).
- **Chấm:** giám khảo Claude qua Anthropic SDK, structured output, không biết model nào viết. Bài viết được bọc trong khối `<scene>` và escape. Code kiểm câu trích của giám khảo có thật trong bài. Số lần chấm và điều kiện chấm thêm: D-25, cờ `--judge-runs`, `--max-judge-runs`, `--rejudge-gap`.
- **Không thành điểm 0:**
  - bài chạm max_tokens (`truncated`), bài rỗng, bài bị lọc nội dung, và bài giám khảo từ chối (`judge_refusal`) được ghi riêng;
  - lỗi API, hết giờ, model trả lời khác model đã yêu cầu thì vào `errors.jsonl` và được chạy lại khi chạy tiếp;
  - model không trả `usage.cost`: ghi `LLM_COST_UNKNOWN`, tính chi phí bằng ước tính tối đa, và bỏ model đó cho phần còn lại của lượt chạy.
- **Kiểm văn bằng code:** bốn bộ kiểm của `writory.quality` (lặp, sáo ngữ, chữ khác hệ, lời thoại), cộng độ dài theo case. Ngưỡng tạm là cờ của bài đo (`--ngram`, `--max-repeats`, `--latin-min`), có ghi vào kết quả. `config/quality.yaml` không đổi.
- **Chỉ số** (`summary.md`, mỗi model một hàng):
  - trung bình ± khoảng tin cậy 95% của từng tiêu chí, tính theo t trên số case, sau khi gộp các mẫu và các lần chấm trong cùng case;
  - tỉ lệ lộ bí mật; số cảnh lọt suy luận hoặc chữ của prompt (`check_meta_leak`, D-30, tính từ văn bản đã lưu); số lỗi kiểm văn; độ dài trung vị;
  - chi phí mỗi cảnh (`usage.cost`); độ trễ; số bài lỗi, bị cắt, hoặc thuộc loại khác.

  Chi phí giám khảo, độ lệch giữa các lần chấm và tỉ lệ câu trích không tìm thấy được ghi riêng.
- **Kiểm giám khảo trước lượt thật** (`judge-check`): chuỗi rỗng, câu "không biết viết", và một cảnh lạc đề phải nhận điểm thấp ở `bam_dan_y` và `hap_dan`. Ngưỡng nằm trong code (`CHECK_LOW_MAX`).
- **Hiệu chỉnh với người chấm:**
  - `export-human` chọn cảnh trải đều theo model và case, xáo thứ tự, ẩn tên model;
  - người chấm điền `human/scores.csv`;
  - `import-human` tính Spearman, tỉ lệ lệch ≤ 1 điểm và độ lệch trung bình người − giám khảo cho từng tiêu chí, rồi ghi vào `summary.md`. Điểm chấm tay 1–5, bước 0,5. Cột `ghi_chu` và dòng không có `scene_id` (góp ý chung) được chép nguyên văn vào mục "Ghi chú của chủ dự án". Dưới 15 cảnh thì báo cáo ghi rõ là chưa đủ để kết luận thứ hạng.
- **Kết quả:** `evals/results/<ngày>-quality-<nhãn>/` gồm `samples.jsonl`, `results.jsonl`, `errors.jsonl`, `traces/`, `meta.json` (commit, sha256 dữ liệu, tham số, trần) và `summary.md`. Kết quả dry-run (`*-dryrun/`) không commit.
- **Key:** chỉ đọc `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY` và, nếu có, `ANTHROPIC_WORKSPACE_ID` (biến môi trường hoặc `--env-file`). Mỗi lệnh chỉ đòi key nó dùng.
- **Trần:** lượt chạy thật bắt buộc có `--budget-openrouter` và `--budget-anthropic` (USD). Trần tính cả chi phí các lần chạy trước trong cùng thư mục. Trước mỗi lời gọi, code giữ chỗ theo chi phí tối đa có thể của lời gọi đó, nên không vượt trần.
- **Mã thoát:** 0 xong; 1 lỗi cấu hình hoặc dữ liệu; 2 dừng vì chạm trần; 3 dừng vì lỗi không chạy tiếp được (key sai, hết credit, yêu cầu tới giám khảo bị từ chối, giám khảo trả lời bằng model khác); 4 kiểm giám khảo không đạt.
- **Loại model khỏi bảng** (`exclude`): lý do và người quyết ghi vào `meta.json`; model đó không vào bảng và không vào `export-human`. Dữ liệu thô và chi phí giữ nguyên.
- Kết quả dùng để cập nhật danh sách model trong `config/models.yaml`.

Lệnh (chạy trong `backend/`):
```bash
uv run python -m writory.quality.bench_d plan --pilot 2                        # ước tính chi phí, không gọi model
uv run python -m writory.quality.bench_d run --label thu --dry-run             # model giả, không mạng
uv run python -m writory.quality.bench_d judge-check --label pilot \
    --off-topic-file <cảnh lạc đề> --budget-anthropic <USD>
uv run python -m writory.quality.bench_d run --label pilot --pilot 2 \
    --budget-openrouter <USD> --budget-anthropic <USD>
uv run python -m writory.quality.bench_d run --out <thư mục kết quả> ...       # chạy tiếp sau khi dừng
uv run python -m writory.quality.bench_d summary --out <thư mục kết quả>
uv run python -m writory.quality.bench_d export-human --out <thư mục kết quả>
uv run python -m writory.quality.bench_d import-human --out <thư mục kết quả>
uv run python -m writory.quality.bench_d exclude --out <thư mục kết quả> --model <id> --reason "<lý do, ai quyết>"
```

## Red-team guardrail
- Dữ liệu: `evals/redteam/`. Mỗi câu có kết quả mong đợi: bị chặn / không lộ / đúng schema.
- Với model giả thì chạy trong test nhanh. Với model thật thì chạy riêng, có trần chi phí.
- G4, prompt injection: `evals/redteam/g4_prompt_injection.yaml`. Phần `expected_wrap` chạy trong test nhanh (`tests/unit/test_safety_wrap.py`). Phần `expected_story` dành cho model thật; lệnh: *(chưa có)*.
- G5, phân loại ô tự viết: `evals/redteam/g5_classify.yaml`, mỗi câu có nhãn mong đợi. Test nhanh chỉ kiểm cấu trúc bộ câu và luồng xử lý (model giả). Đo với model thật: `cd backend && uv run python -m writory.safety.bench_g5 --out ../evals/results/<ngày>-g5` (cần `models.roles.classify`, `limits.input.custom_action_max_chars`, trần `limits.cost_usd.per_story`; chưa chạy).
