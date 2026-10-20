# Bài đo D — 2026-10-19-quality-full

- Tạo: 2026-10-19T23:17:52+07:00; số lần chạy: 2; commit: `1c9aeae8ec`, `7b1a5e9fca`.
- Dữ liệu (`quality/`, sha256): cases.yaml `a12dc3cf7f7f`, rubric.yaml `cc633237b3ca`, models.yaml `26cad3859466`, style_guide_vi.md `f7f2b272078c`.
- Mẫu đề bài: d-brief-1; khung giám khảo: d-judge-1.
- Giám khảo: claude-sonnet-5-5, effort high, thinking adaptive, max_tokens 16000; không fallbacks, không temperature.
- Mỗi (model, case): 1 mẫu. Chấm 2 lần, thêm tới 3 khi một tiêu chí thang 1–5 lệch ≥ 2 hoặc tiêu chí nhị phân bất đồng; điểm cuối = trung vị (D-25).
- Ngưỡng kiểm văn của bài đo: {'ngram_words': 4, 'max_repeats': 2, 'latin_run_min_words': 4} (không đổi config/quality.yaml).
- Đã tiêu: OpenRouter 0.2860 USD (trần lần chạy cuối 2.0), Anthropic 4.3796 USD (trần 12.0).
- Cột tiêu chí: trung bình ± nửa khoảng tin cậy 95% (t, n = số case có điểm). Mỗi case lấy trung bình điểm cuối của các mẫu trước, vì mẫu cùng đề không độc lập.
- Lộ bí mật: số cảnh có điểm cuối `giu_bi_mat` ≤ 0,5 trên số cảnh đã chấm, chỉ tính case có bí mật. Lỗi · cắt · khác: lỗi ở bước viết (errors.jsonl), bài chạm max_tokens, bài rỗng hoặc bị lọc nội dung. Các bài này không vào trung bình.
- Lọt suy luận: số cảnh có thẻ suy luận hoặc chữ của prompt trong văn bản (`check_meta_leak`, D-30) trên số cảnh có văn bản. Tính lại từ samples.jsonl mỗi lần dựng bảng, không gọi model.

| Model | n case | TV tự nhiên | Xưng hô | Bám dàn ý | Cho thấy | Lời thoại | Văn người viết | Muốn đọc tiếp | Lộ bí mật | Lọt suy luận | Lỗi kiểm văn | Độ dài (TV) | USD/cảnh | Trễ s (TV) | Lỗi · cắt · khác |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MiMo 2.6 Flash | 10 | 2.25 ± 0.39 | 3.70 ± 0.70 | 3.60 ± 0.41 | 3.45 ± 0.36 | 3.20 ± 0.25 | 2.80 ± 0.38 | 3.20 ± 0.25 | 0/10 | 0/10 | 2.3 | 3554 | 0.00041 | 13.8 | 0 · 0 · 0 |
| MiMo 2.6 Pro | 10 | 3.45 ± 0.36 | 4.20 ± 0.64 | 3.90 ± 0.41 | 3.70 ± 0.30 | 3.40 ± 0.33 | 3.10 ± 0.28 | 3.60 ± 0.37 | 0/10 | 1/10 | 1.3 | 3640 | 0.00141 | 64.2 | 0 · 0 · 0 |
| DeepSeek V4.1 Flash | 10 | 3.85 ± 0.34 | 4.25 ± 0.64 | 3.85 ± 0.29 | 3.90 ± 0.23 | 3.90 ± 0.23 | 3.40 ± 0.33 | 3.95 ± 0.11 | 1/10 | 0/10 | 1.4 | 4626 | 0.00083 | 18.9 | 0 · 0 · 0 |
| Gemini 3.5 F-Lite | 10 | 2.90 ± 0.28 | 3.90 ± 0.79 | 3.45 ± 0.49 | 3.20 ± 0.30 | 3.05 ± 0.36 | 2.70 ± 0.30 | 3.15 ± 0.24 | 1/10 | 0/10 | 0.8 | 3784 | 0.00316 | 7.4 | 0 · 0 · 0 |
| GPT-6 Luna | 10 | 4.00 ± 0.00 | 4.65 ± 0.38 | 4.60 ± 0.33 | 4.05 ± 0.11 | 3.80 ± 0.30 | 3.90 ± 0.15 | 3.90 ± 0.23 | 0/10 | 0/10 | 0.3 | 3316 | 0.00070 | 10.2 | 0 · 0 · 0 |
| Qwen 3.7 Plus | 10 | 2.40 ± 0.53 | 4.15 ± 0.63 | 3.45 ± 0.31 | 3.00 ± 0.00 | 2.90 ± 0.23 | 2.10 ± 0.23 | 3.10 ± 0.15 | 0/10 | 0/10 | 2.6 | 4984 | 0.00210 | 26.4 | 0 · 0 · 0 |
| MiniMax M3 | 10 | 3.10 ± 0.41 | 4.15 ± 0.53 | 3.85 ± 0.45 | 3.35 ± 0.34 | 3.20 ± 0.25 | 2.90 ± 0.23 | 3.45 ± 0.31 | 0/10 | 0/10 | 1.6 | 3652 | 0.00282 | 27.3 | 0 · 0 · 0 |
| Qwen 3.8 Flash | 10 | 2.90 ± 0.23 | 3.60 ± 0.67 | 3.20 ± 0.45 | 3.00 ± 0.00 | 3.00 ± 0.00 | 2.10 ± 0.23 | 3.00 ± 0.00 | 2/10 | 0/10 | 4.3 | 4244 | 0.00064 | 33.1 | 0 · 0 · 0 |
| GPT-6.1 Sol (mốc) | 10 | 4.00 ± 0.00 | 4.85 ± 0.17 | 4.75 ± 0.25 | 4.50 ± 0.34 | 4.00 ± 0.00 | 4.05 ± 0.11 | 4.05 ± 0.11 | 0/10 | 0/10 | 0.9 | 3689 | 0.01619 | 42.8 | 0 · 0 · 0 |

Model bị loại khỏi bảng (dữ liệu thô vẫn nằm trong samples/results/errors.jsonl; chi phí vẫn tính vào tổng):
- Mistral Small 4 (`mistralai/mistral-small-2603`): Loại khỏi bài đo theo quyết định chủ dự án (20/10): lỗi 429 liên tục, 4/10 case

## Giám khảo và chi phí
- Lần chấm: 190 hợp lệ, 0 từ chối, 0 lỗi. Cảnh chấm quá 2 lần: 2/94.
- Model thực trả lời: claude-sonnet-5-5.
- Chi phí mỗi lần chấm (USD): min 0.0162 · trung vị 0.0212 · max 0.0469; tổng 4.3796.
- Chi phí mỗi cảnh viết (USD): min 0.00018 · trung vị 0.00132 · max 0.01741; tổng 0.2860.
- Token vào đọc từ cache: 914517/1405600 (65%).
- Câu trích của giám khảo không tìm thấy trong bài: 24/1420.
- Độ lệch giữa các lần chấm (trung bình max−min mỗi cảnh): tieng_viet_tu_nhien 0.16, xung_ho 0.26, bam_dan_y 0.26, cho_thay 0.10, loi_thoai 0.09, van_nguoi 0.16, hap_dan 0.12, giu_bi_mat 0.02.

## Đồng thuận người chấm – giám khảo
| Tiêu chí | n | Spearman | Lệch ≤ 1 điểm | Người − giám khảo (TB) |
|---|---|---|---|---|
| tieng_viet_tu_nhien | 6 | 0.32 | 67% | +0.92 |
| van_nguoi | 6 | 0.68 | 67% | +0.92 |
| hap_dan | 6 | 0.31 | 100% | +0.67 |

Mới có 6 cảnh chấm tay (< 15): chỉ để tham khảo, chưa đủ để kết luận thứ hạng model.

## Ghi chú của chủ dự án
Chép nguyên văn từ `human/scores.csv`; id cảnh ẩn danh.

- S01: giữa cuộc hội thoại không miêu tả tâm lý nhân vật, nên có 1 dòng ngắn để người đọc tưởng tưởng được cảm xúc và hành động của nhân vật nam
- S02: 1. Các câu nói không xuống dòng; 2. với thể loại giả tưởng này nếu user không yêu cầu gì thì nên ghi địa danh giả, tên nhân vật nên kiểu Trung quốc hán việt thay vì tên Việt Nam
- S03: Bài này làm được cả 2 thứ tôi feedback cho 2 bài trên, nhưng vẫn đang dùng địa điểm thật, và các từ như "đường trống" hơi kém (nên là "đường vắng" ), hoặc "Cô nghe ngóng" nghe rất cụt ngủn
- S04: 1. Xưng ngôi thứ nhất nên xưng là "Tôi" thay vì "Tao"; 2. Lặp từ "Tao" quá nhiều vì đang ở ngôi thứ nhất, nhưng do viết kém nên bị lặp
- S05: Viết tốt, văn phong chưa hay lắm, nhưng có thể chấp nhận
- S06: nội dung chứa ký tự lạ "bềnh trên mặt汤", " không chút起伏"
- S10: Văn phong chưa hợp truyện, "giết người đoạt bảo" thay vì "chuyên lấy mạng người mang hành lý quý giá" và nhiều cầu từ kahsc chưa hợp ; hội thoại của truyện kiếm hiệp  nên xuống dòng, "" chỉ dành cho truyền đạt lời
- S11: như trên , "Ta đứng ngay ngoài này, đệ cứ yên tâm." -> "ta hộ pháp cho đệ"
- (chung) Feedback chung : 1. backend thay toàn bộ " — " bằng " - " nhé;

