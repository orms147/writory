# Đo lại khởi tạo `setup-11` (D-135), so với `setup-10`: khai trước khi chạy

Người đọc: Claude và chủ dự án. Viết 30/10/2026, **trước** khi chạy; sau khi chạy, số liệu ở `compare.json`, nhận xét ở `notes.md` cùng thư mục, file này không sửa.

## Đổi gì
`setup-11` (D-135): mỗi mạch phải gỡ khai `answered_by`, các `fact_id` bí mật trả lời câu hỏi chính của nó; đề nêu luật "khoảng gỡ không bắt đầu trước `reveal_from_chapter` của bí mật đó". Code kiểm ở bước dựng: lệch thì dời khoảng gỡ (`story_plan.align_thread_windows`), không tốn lượt sửa; id không phải bí mật của kế hoạch là lỗi `answered_by`, đi lượt sửa D-54. Đề `build` dài thêm 481 ký tự (cả mức ngắn lẫn dài); câu mở lượt sửa dài thêm 132 ký tự.

Mốc so: năm lượt `setup-10` của `../2026-10-29-setup10-check/` (`compare.json`, `notes.md`), cùng năm đề, cùng seed của đề, cùng model `openai/gpt-6-luna` (`reasoning: low`) cho vai `setup`. Config khác lượt đó ở phần không chạm khởi tạo: `limits.retries.llm_transient` 2 → 3 và chờ lùi (D-123), vai `video` và `limits.video_export` (D-125, D-127). Hai đổi đầu chỉ có tác dụng khi có lỗi mạng.

## Lệnh
Chạy từ `backend/` của nhánh `feature/plan-thread-secret-window`, cây sạch (commit đã đẩy lên PR), một chuỗi nối tiếp, không chạy song song chuỗi nào khác:

```bash
cd backend
for x in "ab-tu-tien 0.018" "ab-ky-ao 0.018" "ab-trinh-tham 0.018" "long-tu-tien 0.023" "long-ky-ao-hanh-trinh 0.023"; do
  set -- $x
  uv run python -m writory.pipeline.bench_run --label setup11-$1 \
    --scenario ../evals/scenarios/story_run/$1.yaml --setup-only --budget $2 \
    --env-file <đường dẫn .env của repo chính>
done
uv run python ../evals/results/2026-10-30-setup11-check/aggregate.py ../evals/results/*-run-setup11-*
uv run python ../evals/results/2026-10-30-plan-thread-secret-window/count_plans.py \
  > ../evals/results/2026-10-30-setup11-check/count_plans_after.txt
```

Một lượt lỗi (khởi tạo hỏng, chạm trần) không dừng chuỗi: nó là một điểm dữ liệu. Không `--seed`: dùng seed của đề, như `setup-10`. Thư mục kết quả là `evals/results/<ngày chạy>-run-setup11-<đề>/`.

**Trần:** `--budget` là trần của từng lượt, nên tổng tối đa là 3 × 0.018 + 2 × 0.023 = **0.100 USD**. Mỗi trần đủ cho đường xấu nhất đã thấy ở `setup-10` (ba bước đề xuất, hai lượt "bấm thử lại", mỗi lượt một lần dựng và một lượt sửa), vì trước mỗi lời gọi lệnh giữ chỗ `max_tokens_per_call` × giá ra, khoảng 0.0087 USD. **Ước tính:** khoảng 0.03 USD (năm lượt `setup-10` tốn 0.0263 USD; phần đề thêm chừng 150–250 token vào mỗi lần dựng, dưới 0.0001 USD mỗi lượt).

Dry-run đã chạy đủ năm lệnh trên với `--dry-run --out <thư mục tạm>` (model giả, không key) và `aggregate.py` đọc được kết quả; lượt dry-run bị `aggregate.py` đánh dấu không hợp lệ, đúng như mong đợi.

## Số đo
Lấy bằng `aggregate.py` từ `report.json` (`thread_answers`, `setup_repairs`, `cost`, `appearance_variety`), `meta.json` và `calls.jsonl`:

1. **Có liên kết:** số mạch phải gỡ có `answered_by` trên tổng số mạch phải gỡ; số kế hoạch có ít nhất một liên kết.
2. **Lệch thô trước khi dời:** số mạch code đã dời (`shifted`), và số phải dời cả hạn (`shifted_end`, hạn cũ trước cả khoảng lộ).
3. **Lệch sau khi dời:** `mismatches` trên kế hoạch cuối; phải bằng 0.
4. **Lượt sửa D-54:** số lượt cần sửa, loại lỗi, số lượt có lỗi `answered_by`; số khởi tạo hỏng.
5. **Chi phí:** chi phí vai `setup` trung bình mỗi lượt; token vào và ra của lần dựng đầu.
6. **Ngoại hình** (`appearance_variety`, D-122): tổng mở bằng "Trông", mở trùng, trùng màu tóc.
7. **Đọc tay** (`truth_dump.json`): mỗi liên kết, mô tả mạch đối với chữ Fact của bí mật. Liên kết **đúng** khi bí mật trả lời câu hỏi chính của mạch (cả câu hoặc phần quyết định). Liên kết sai mà gây dời là **dời oan**, đếm riêng.
8. **Liên kết sót:** các cặp `count_plans.py` (heuristic H1/H2) bắt được trên kế hoạch `setup-11` mà model không khai, đọc tay xem có thật gắn nhau không. Chỉ là ước lượng, vì heuristic có thể đếm thừa hoặc sót.

## Mốc `setup-10` và dự đoán
| | setup-10 (5 lượt) | dự đoán setup-11 |
|---|---|---|
| Mạch phải gỡ | 24 | cùng cỡ |
| Kế hoạch có cặp mạch–bí mật gắn nhau (heuristic, `count_plans.txt`) | 4/5 | ≥ 4/5 có liên kết khai |
| Cặp lệch (heuristic); cặp nặng | 5 trong 4/5 kế hoạch; 3 | lệch thô (`shifted`) ít hơn 5, vì đề nêu luật; `shifted_end` ≤ 2 |
| Lệch sau khi dời | không đo được | 0 |
| Lượt cần sửa D-54 | 2/5 (`milestones`; `edges` + `pacing`) | 1–3/5, không thêm lỗi `answered_by` ở quá 1 lượt |
| Khởi tạo hỏng | 0 | 0 |
| Chi phí `setup` trung bình (USD) | 0.00527 | ≤ 0.0066 (nhiễu của lượt sửa lớn hơn phần đề thêm) |
| Token vào lần dựng đầu, trung bình | 4318.8 | +150 tới +250 |
| Token ra lần dựng đầu, trung bình | 4905 | cùng cỡ (mỗi mạch thêm vài id) |
| Ngoại hình: "Trông" / mở trùng / trùng tóc (26 nhân vật) | 0 / 3 / 6 | cùng cỡ |

Số cặp heuristic của `setup-10` không cùng thước với `shifted`: heuristic đoán liên kết bằng chữ, `shifted` dùng liên kết model khai. So sánh chỉ ở mức "đề nêu luật thì model có tự xếp đúng hơn không".

## Luật quyết định (khai trước)
- **C0 hợp lệ:** đủ năm lượt thật, commit sạch của nhánh, `prompt_versions.setup` = `setup-11`, model vai `setup` như mốc. Thiếu thì chạy bù đúng lượt thiếu, không tính lượt hỏng vì lỗi mạng.
- **C1 đúng code (bắt buộc):** `mismatches` = 0 ở cả năm lượt. Trượt là lỗi code: không kết luận gì về đề, sửa và thêm test hồi quy trước khi gộp.
- **C2 không làm hỏng khởi tạo:** năm/năm khởi tạo xong, và lỗi `answered_by` xuất hiện ở lượt sửa của tối đa 1/5 lượt. Trượt: đề làm model khai sai id thường xuyên; hỏi chủ dự án chọn sửa đề (`setup-12`, đo lại) hay để code bỏ id lạ không tốn lượt sửa (như D-76).
- **C3 model dùng trường:** ít nhất 4/5 kế hoạch có một liên kết. Trượt: code vô hại (không liên kết thì không dời) nên gộp được, nhưng ghi rõ tính năng chưa chạy và sửa đề sau.
- **C4 liên kết đúng nghĩa (đọc tay):** ít nhất 80% liên kết đúng. Dời oan nào làm dời cả hạn thì ghi riêng. Trượt: sửa đề trước khi gộp.
- **Theo dõi, không phải luật:** chi phí trung bình quá 1.5 lần mốc (`aggregate.py` in "xem lại"), ngoại hình lệch xa mốc, nhiều liên kết sót: ghi vào `notes.md`, không chặn.

Kết luận: C0 tới C4 đạt thì giữ `setup-11`. C1 trượt thì chặn. C2 hay C4 trượt thì sửa trước khi gộp. Chỉ C3 trượt thì gộp được, ghi điểm yếu.

## Hạn chế đã biết
- Mẫu nhỏ (5 lượt, một seed mỗi đề), như `setup-10`; tỉ lệ sửa và chi phí không phân biệt được ở cỡ này.
- Model không tất định: cùng seed không ra cùng thế giới, nên chỉ so tỉ lệ, không so từng mạch.
- Phép đo này chỉ đo kế hoạch lúc khởi tạo. Khoảng gỡ đã dời có làm dàn ý bớt giục gỡ mạch trước khi bí mật lộ hay không thì chưa đo; phép đo dàn ý ch8 (`../2026-10-30-outline-next-milestone/`) cho thấy riêng mạch lệch khoảng chưa đẩy dàn ý tới bí mật.
