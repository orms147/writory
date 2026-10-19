# Bài đo D — 2026-10-19-quality-pilot

- Tạo: 2026-10-19T23:00:02+07:00; số lần chạy: 3; commit: `40f871439a`, `b010954e44`, `b010954e44` (dirty).
- Dữ liệu (`quality/`, sha256): cases.yaml `a12dc3cf7f7f`, rubric.yaml `cc633237b3ca`, models.yaml `0c8a942a0ea5`, style_guide_vi.md `f7f2b272078c`.
- Mẫu đề bài: d-brief-1; khung giám khảo: d-judge-1.
- Giám khảo: claude-sonnet-5-5, effort high, thinking adaptive, max_tokens 16000; không fallbacks, không temperature.
- Mỗi (model, case): 1 mẫu. Chấm 2 lần, thêm tới 3 khi một tiêu chí thang 1–5 lệch ≥ 2 hoặc tiêu chí nhị phân bất đồng; điểm cuối = trung vị (D-25).
- Ngưỡng kiểm văn của bài đo: {'ngram_words': 4, 'max_repeats': 2, 'latin_run_min_words': 4} (không đổi config/quality.yaml).
- Đã tiêu: OpenRouter 0.0249 USD (trần lần chạy cuối 0.5), Anthropic 0.8003 USD (trần 3.0).
- Lần chạy 2026-10-19T23:00:02+07:00: dừng (abort: giám khảo: LLM_REQUEST_INVALID: HTTP 400: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'This API key is not scoped to a workspace, so this request must include the anthropic-workspace-id header with the ID of the workspace to use. Add the header, or use an API key that is scoped to a workspace.'}, 'request_id': 'req_011CgBsetsAWBoBmaaDSHeAV'}).
- Cột tiêu chí: trung bình ± nửa khoảng tin cậy 95% (t, n = số case có điểm). Mỗi case lấy trung bình điểm cuối của các mẫu trước, vì mẫu cùng đề không độc lập.
- Lộ bí mật: số cảnh có điểm cuối `giu_bi_mat` ≤ 0,5 trên số cảnh đã chấm, chỉ tính case có bí mật. Lỗi · cắt · khác: lỗi ở bước viết (errors.jsonl), bài chạm max_tokens, bài rỗng hoặc bị lọc nội dung. Các bài này không vào trung bình.

| Model | n case | TV tự nhiên | Xưng hô | Bám dàn ý | Cho thấy | Lời thoại | Văn người viết | Muốn đọc tiếp | Lộ bí mật | Lỗi kiểm văn | Độ dài (TV) | USD/cảnh | Trễ s (TV) | Lỗi · cắt · khác |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MiMo 2.6 Flash | 2 | 2.25 ± 3.18 | 2.50 ± 12.71 | 3.50 ± 6.35 | 3.25 ± 3.18 | 2.75 ± 3.18 | 2.75 ± 3.18 | 3.00 ± 0.00 | 0/2 | 1.0 | 3618 | 0.00035 | 17.8 | 0 · 0 · 0 |
| MiMo 2.6 Pro | 2 | 4.00 ± 0.00 | 3.50 ± 12.71 | 4.00 ± 0.00 | 4.00 ± 0.00 | 3.75 ± 3.18 | 3.25 ± 3.18 | 4.00 ± 0.00 | 0/2 | 1.0 | 3552 | 0.00160 | 49.3 | 0 · 0 · 0 |
| DeepSeek V4.1 Flash | 2 | 3.50 ± 6.35 | 4.50 ± 6.35 | 3.50 ± 6.35 | 4.00 ± 0.00 | 4.00 ± 0.00 | 3.00 ± 0.00 | 4.00 ± 0.00 | 0/2 | 9.5 | 4661 | 0.00088 | 24.4 | 0 · 0 · 0 |
| Gemini 3.5 F-Lite | 2 | 3.00 ± 0.00 | 2.75 ± 9.53 | 3.25 ± 9.53 | 3.50 ± 6.35 | 3.00 ± 0.00 | 3.00 ± 0.00 | 3.50 ± 0.00 | 0/2 | 0.5 | 3496 | 0.00326 | 8.7 | 0 · 0 · 0 |
| GPT-6 Luna | 2 | 4.00 ± 0.00 | 4.75 ± 3.18 | 4.75 ± 3.18 | 4.00 ± 0.00 | 4.00 ± 0.00 | 4.00 ± 0.00 | 4.00 ± 0.00 | 0/2 | 0.5 | 3296 | 0.00075 | 11.2 | 0 · 0 · 0 |
| Qwen 3.7 Plus | 2 | 2.50 ± 6.35 | 3.25 ± 15.88 | 3.00 ± 0.00 | 3.00 ± 0.00 | 3.00 ± 0.00 | 2.00 ± 0.00 | 3.00 ± 0.00 | 0/2 | 2.0 | 6026 | 0.00248 | 34.8 | 0 · 0 · 0 |
| MiniMax M3 | 2 | 3.50 ± 6.35 | 3.25 ± 9.53 | 3.75 ± 3.18 | 4.00 ± 0.00 | 3.00 ± 0.00 | 3.00 ± 0.00 | 3.50 ± 6.35 | 0/2 | 2.5 | 3306 | 0.00238 | 29.6 | 0 · 0 · 0 |
| Mistral Small 4 | 0 | — | — | — | — | — | — | — | — | — | — | — | — | 2 · 0 · 0 |
| Qwen 3.8 Flash | 2 | 2.50 ± 6.35 | 1.75 ± 3.18 | 3.25 ± 9.53 | 3.00 ± 0.00 | 2.75 ± 3.18 | 2.00 ± 0.00 | 3.00 ± 0.00 | 0/2 | 1.5 | 4798 | 0.00076 | 35.4 | 0 · 0 · 0 |
| GPT-6.1 Sol (mốc) | 0 | — | — | — | — | — | — | — | — | — | — | — | — | 1 · 0 · 0 |

## Giám khảo và chi phí
- Lần chấm: 33 hợp lệ, 0 từ chối, 0 lỗi. Cảnh chấm quá 2 lần: 1/16.
- Model thực trả lời: claude-sonnet-5-5.
- Chi phí mỗi lần chấm (USD): min 0.0173 · trung vị 0.0223 · max 0.0379; tổng 0.7612.
- Chi phí mỗi cảnh viết (USD): min 0.00028 · trung vị 0.00150 · max 0.00335; tổng 0.0249.
- Token vào đọc từ cache: 162367/250473 (65%).
- Câu trích của giám khảo không tìm thấy trong bài: 0/248.
- Độ lệch giữa các lần chấm (trung bình max−min mỗi cảnh): tieng_viet_tu_nhien 0.06, xung_ho 0.69, bam_dan_y 0.25, cho_thay 0.06, loi_thoai 0.19, van_nguoi 0.19, hap_dan 0.12, giu_bi_mat 0.00.

## Kiểm giám khảo trên bài tồi (phải ≤ 2 ở bam_dan_y, hap_dan)
- empty (tu-tien-dot-pha): đạt — tieng_viet_tu_nhien 1, xung_ho 1, bam_dan_y 1, cho_thay 1, loi_thoai 1, van_nguoi 1, hap_dan 1, giu_bi_mat 1.
- dont_know (tu-tien-dot-pha): đạt — tieng_viet_tu_nhien 1, xung_ho 1, bam_dan_y 1, cho_thay 1, loi_thoai 1, van_nguoi 1, hap_dan 1, giu_bi_mat 1.
- off_topic (tu-tien-dot-pha): đạt — tieng_viet_tu_nhien 4, xung_ho 1, bam_dan_y 1, cho_thay 5, loi_thoai 5, van_nguoi 5, hap_dan 2, giu_bi_mat 1.

