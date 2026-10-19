# Bài đo D — 2026-10-19-quality-pilot

- Tạo: 2026-10-19T23:00:02+07:00; số lần chạy: 1; commit: `40f871439a`.
- Dữ liệu (`quality/`, sha256): cases.yaml `a12dc3cf7f7f`, rubric.yaml `cc633237b3ca`, models.yaml `0c8a942a0ea5`, style_guide_vi.md `f7f2b272078c`.
- Mẫu đề bài: d-brief-1; khung giám khảo: d-judge-1.
- Giám khảo: claude-sonnet-5-5, effort high, thinking adaptive, max_tokens 16000; không fallbacks, không temperature.
- Mỗi (model, case): ? mẫu. Chấm ? lần, thêm tới ? khi một tiêu chí thang 1–5 lệch ≥ ? hoặc tiêu chí nhị phân bất đồng; điểm cuối = trung vị (D-25).
- Ngưỡng kiểm văn của bài đo: ? (không đổi config/quality.yaml).
- Đã tiêu: OpenRouter 0.0000 USD (trần lần chạy cuối ?), Anthropic 0.0000 USD (trần ?).
- Lần chạy 2026-10-19T23:00:02+07:00: dừng (abort: giám khảo: LLM_REQUEST_INVALID: HTTP 400: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'This API key is not scoped to a workspace, so this request must include the anthropic-workspace-id header with the ID of the workspace to use. Add the header, or use an API key that is scoped to a workspace.'}, 'request_id': 'req_011CgBsetsAWBoBmaaDSHeAV'}).
- Cột tiêu chí: trung bình ± nửa khoảng tin cậy 95% (t, n = số case có điểm). Mỗi case lấy trung bình điểm cuối của các mẫu trước, vì mẫu cùng đề không độc lập.
- Lộ bí mật: số cảnh có điểm cuối `giu_bi_mat` ≤ 0,5 trên số cảnh đã chấm, chỉ tính case có bí mật. Lỗi · cắt · khác: lỗi ở bước viết (errors.jsonl), bài chạm max_tokens, bài rỗng hoặc bị lọc nội dung. Các bài này không vào trung bình.

| Model | n case | TV tự nhiên | Xưng hô | Bám dàn ý | Cho thấy | Lời thoại | Văn người viết | Muốn đọc tiếp | Lộ bí mật | Lỗi kiểm văn | Độ dài (TV) | USD/cảnh | Trễ s (TV) | Lỗi · cắt · khác |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Giám khảo và chi phí
- Lần chấm: 0 hợp lệ, 0 từ chối, 0 lỗi. Cảnh chấm quá 2 lần: 0/0.
- Model thực trả lời: —.
- Chi phí mỗi lần chấm (USD): —; tổng 0.0000.
- Chi phí mỗi cảnh viết (USD): —; tổng 0.0000.
- Token vào đọc từ cache: 0/0.
- Câu trích của giám khảo không tìm thấy trong bài: 0/0.

