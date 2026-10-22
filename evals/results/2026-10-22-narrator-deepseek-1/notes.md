# Nhận xét đọc tay: narrator-deepseek-1 (DeepSeek V4 Flash, bài E đề v2)

Người đọc: Claude (nhánh feature/model-deepseek), 22/10/2026. Nguồn: `summary.md`, `results.jsonl`. D-100.

Lệnh: `uv run --group eval python -m writory.pipeline.bench_e run --label deepseek-1 --questions-file questions-v2.yaml --samples 1 --budget 0.04 --env-file C:/Work/AI/WriTory/.env`. Một lần mỗi câu, không giám khảo. Người kể là `deepseek/deepseek-v4-flash`, suy luận low, đề `narrator-3`. So với Luna: `evals/results/2026-10-21-narrator-v2-d78-judge/` (3 lần mỗi câu).

| | DeepSeek (1 lần, 108 lượt) | Luna d78-judge (3 lần, 324 lượt) |
|---|---|---|
| Lộ câu cuối / câu thô | 0 / 0 | 0 / 0 |
| Loại a đạt | 32/35 (91%) [78–97] | 101/105 (96%) |
| Loại b, c, d, e, f | 17/17, 23/23, 13/13, 15/15, 5/5 | 100%, 100%, 37/39, 100%, 100% |
| Lỗi lời gọi | 0 | 0 |
| Chi phí thật | 0,0343 USD | 0,0231 USD |

- **Lộ bằng 0** (điều kiện bắt buộc); b–f không tụt. Loại a thấp hơn một chút nhưng khoảng tin cậy chồng nhau (35 lượt); ba lượt không đạt đều là `declined` ở `c1-a-ten-kiem`, `c2-a-chen-lenh-hoi-da-biet`, `p5-a-kiem-nam-o-dau` (hai câu đầu cũng là điểm yếu của Luna, `p5-a-kiem-nam-o-dau` là câu truy hồi sổ tay lớn).
- **Chi phí:** 108 lượt tốn 0,0343 USD, tức khoảng 0,000318 mỗi lời gọi; Luna 0,0231 USD cho 324 lượt (khoảng 0,000071 mỗi lời gọi): DeepSeek đắt hơn khoảng 4,5 lần mỗi lời gọi, vì token ra trung bình 326 so với khoảng 31 của Luna (người kể trả câu ngắn nhưng DeepSeek có suy luận). 74/108 lời gọi có token cache.
- Không lượt nào bị lưới `meta_hedge` đổi; không `errors.jsonl`.

## Chưa kiểm
- 1 lần mỗi câu, không giám khảo (`goi_y_an`, `vuot_so_tay` chưa chấm), nên "không úp mở" mới kiểm bằng lưới code.
