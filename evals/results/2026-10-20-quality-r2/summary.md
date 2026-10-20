# Bài đo D — 2026-10-20-quality-r2

- Tạo: 2026-10-20T13:15:29+07:00; số lần chạy: 1; commit: `d4d66da340`.
- Dữ liệu (`quality/`, sha256): cases.yaml `97aa056aeb4e`, rubric.yaml `cc601304bc47`, models.yaml `2a1a7a57f57e`, style_guide_vi.md `1986226a9c6d`.
- Mẫu đề bài: d-brief-2; khung giám khảo: d-judge-1.
- Giám khảo: claude-sonnet-5-5, effort high, thinking adaptive, max_tokens 16000; không fallbacks, không temperature.
- Mỗi (model, case): 1 mẫu. Chấm 2 lần, thêm tới 3 khi một tiêu chí thang 1–5 lệch ≥ 2 hoặc tiêu chí nhị phân bất đồng; điểm cuối = trung vị (D-25).
- Ngưỡng kiểm văn của bài đo: {'ngram_words': 4, 'max_repeats': 2, 'latin_run_min_words': 4} (không đổi config/quality.yaml).
- Đã tiêu: OpenRouter 0.1772 USD (trần lần chạy cuối 0.5), Anthropic 1.9951 USD (trần 4.0).
- Cột tiêu chí: trung bình ± nửa khoảng tin cậy 95% (t, n = số case có điểm). Mỗi case lấy trung bình điểm cuối của các mẫu trước, vì mẫu cùng đề không độc lập.
- Lộ bí mật: số cảnh có điểm cuối `giu_bi_mat` ≤ 0,5 trên số cảnh đã chấm, chỉ tính case có bí mật. Lỗi · cắt · khác: lỗi ở bước viết (errors.jsonl), bài chạm max_tokens, bài rỗng hoặc bị lọc nội dung. Các bài này không vào trung bình.
- Lọt suy luận: số cảnh có thẻ suy luận hoặc chữ của prompt trong văn bản (`check_meta_leak`, D-30) trên số cảnh có văn bản. Tính lại từ samples.jsonl mỗi lần dựng bảng, không gọi model.

| Model | n case | TV tự nhiên | Xưng hô | Bám dàn ý | Cho thấy | Lời thoại | Văn người viết | Muốn đọc tiếp | Thể loại | Lộ bí mật | Lọt suy luận | Lỗi kiểm văn | Độ dài (TV) | USD/cảnh | Trễ s (TV) | Lỗi · cắt · khác |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GPT-6 Luna | 10 | 4.00 ± 0.00 | 4.60 ± 0.33 | 4.40 ± 0.28 | 4.05 ± 0.11 | 3.55 ± 0.36 | 3.90 ± 0.23 | 3.95 ± 0.11 | 4.90 ± 0.15 | 0/10 | 0/10 | 0.7 | 3241 | 0.00064 | 14.2 | 0 · 0 · 0 |
| DeepSeek V4.1 Flash | 10 | 3.60 ± 0.33 | 4.35 ± 0.48 | 3.90 ± 0.23 | 3.75 ± 0.25 | 3.65 ± 0.29 | 3.25 ± 0.30 | 3.85 ± 0.24 | 4.40 ± 0.41 | 0/10 | 0/10 | 1.2 | 4392 | 0.00171 | 41.1 | 0 · 0 · 0 |
| Qwen 3.8 Flash | 10 | 2.70 ± 0.35 | 3.85 ± 0.79 | 3.30 ± 0.56 | 2.95 ± 0.11 | 3.00 ± 0.00 | 2.00 ± 0.00 | 3.00 ± 0.00 | 3.80 ± 0.30 | 1/10 | 0/10 | 1.2 | 4803 | 0.00068 | 39.6 | 0 · 0 · 0 |
| MiniMax M3.1 F free | 0 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | 1 · 0 · 0 |
| GPT-6.1 Sol (mốc) | 10 | 4.00 ± 0.00 | 4.50 ± 0.29 | 4.80 ± 0.25 | 4.30 ± 0.30 | 3.95 ± 0.11 | 4.00 ± 0.00 | 4.05 ± 0.11 | 4.95 ± 0.11 | 0/10 | 0/10 | 1.1 | 3754 | 0.01469 | 50.5 | 0 · 0 · 0 |

## Giám khảo và chi phí
- Lần chấm: 81 hợp lệ, 0 từ chối, 0 lỗi. Cảnh chấm quá 2 lần: 1/40.
- Model thực trả lời: claude-sonnet-5-5.
- Chi phí mỗi lần chấm (USD): min 0.0181 · trung vị 0.0232 · max 0.0477; tổng 1.9951.
- Chi phí mỗi cảnh viết (USD): min 0.00052 · trung vị 0.00101 · max 0.01774; tổng 0.1772.
- Token vào đọc từ cache: 448828/670175 (67%).
- Câu trích của giám khảo không tìm thấy trong bài: 12/676.
- Độ lệch giữa các lần chấm (trung bình max−min mỗi cảnh): tieng_viet_tu_nhien 0.05, xung_ho 0.20, bam_dan_y 0.20, cho_thay 0.17, loi_thoai 0.12, van_nguoi 0.03, hap_dan 0.07, quy_uoc_the_loai 0.15, giu_bi_mat 0.03.

