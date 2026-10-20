# Bài đo D — 2026-10-20-quality-r2-minimax

- Tạo: 2026-10-20T13:28:57+07:00; số lần chạy: 1; commit: `d4d66da340` (dirty).
- Dữ liệu (`quality/`, sha256): cases.yaml `97aa056aeb4e`, rubric.yaml `cc601304bc47`, models.yaml `b276e8a57e8b`, style_guide_vi.md `1986226a9c6d`.
- Mẫu đề bài: d-brief-2; khung giám khảo: d-judge-1.
- Giám khảo: claude-sonnet-5-5, effort high, thinking adaptive, max_tokens 16000; không fallbacks, không temperature.
- Mỗi (model, case): 1 mẫu. Chấm 2 lần, thêm tới 3 khi một tiêu chí thang 1–5 lệch ≥ 2 hoặc tiêu chí nhị phân bất đồng; điểm cuối = trung vị (D-25).
- Ngưỡng kiểm văn của bài đo: {'ngram_words': 4, 'max_repeats': 2, 'latin_run_min_words': 4} (không đổi config/quality.yaml).
- Đã tiêu: OpenRouter 0.0000 USD (trần lần chạy cuối 0.1), Anthropic 0.4950 USD (trần 1.0).
- Cột tiêu chí: trung bình ± nửa khoảng tin cậy 95% (t, n = số case có điểm). Mỗi case lấy trung bình điểm cuối của các mẫu trước, vì mẫu cùng đề không độc lập.
- Lộ bí mật: số cảnh có điểm cuối `giu_bi_mat` ≤ 0,5 trên số cảnh đã chấm, chỉ tính case có bí mật. Lỗi · cắt · khác: lỗi ở bước viết (errors.jsonl), bài chạm max_tokens, bài rỗng hoặc bị lọc nội dung. Các bài này không vào trung bình.
- Lọt suy luận: số cảnh có thẻ suy luận hoặc chữ của prompt trong văn bản (`check_meta_leak`, D-30) trên số cảnh có văn bản. Tính lại từ samples.jsonl mỗi lần dựng bảng, không gọi model.

| Model | n case | TV tự nhiên | Xưng hô | Bám dàn ý | Cho thấy | Lời thoại | Văn người viết | Muốn đọc tiếp | Thể loại | Lộ bí mật | Lọt suy luận | Lỗi kiểm văn | Độ dài (TV) | USD/cảnh | Trễ s (TV) | Lỗi · cắt · khác |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MiniMax M3.1 F free | 10 | 1.60 ± 0.37 | 3.05 ± 0.59 | 2.60 ± 0.50 | 3.05 ± 0.26 | 2.60 ± 0.28 | 2.30 ± 0.25 | 2.75 ± 0.30 | 3.45 ± 0.31 | 2/10 | 0/10 | 1.4 | 4761 | 0.00000 | 41.7 | 0 · 0 · 0 |

## Giám khảo và chi phí
- Lần chấm: 20 hợp lệ, 0 từ chối, 0 lỗi. Cảnh chấm quá 2 lần: 0/10.
- Model thực trả lời: claude-sonnet-5-5.
- Chi phí mỗi lần chấm (USD): min 0.0206 · trung vị 0.0244 · max 0.0347; tổng 0.4950.
- Chi phí mỗi cảnh viết (USD): min 0.00000 · trung vị 0.00000 · max 0.00000; tổng 0.0000.
- Token vào đọc từ cache: 105857/176484 (60%).
- Câu trích của giám khảo không tìm thấy trong bài: 3/170.
- Độ lệch giữa các lần chấm (trung bình max−min mỗi cảnh): tieng_viet_tu_nhien 0.00, xung_ho 0.50, bam_dan_y 0.00, cho_thay 0.10, loi_thoai 0.40, van_nguoi 0.40, hap_dan 0.10, quy_uoc_the_loai 0.30, giu_bi_mat 0.00.

